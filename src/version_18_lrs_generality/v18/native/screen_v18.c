/*
 * screen_v18.c -- V18 generality study: compiled search with additional schedulers and optional stage timing.
 *
 * The candidate model is IDENTICAL to code/native/screen_core.c (V17), which is itself checked against the Python
 * oracle: beam = ZF/RZF with unit-norm columns, robust coefficients a_k, F, u, coupling test by M-matrix pivots,
 * power p = (I - F)^{-1} u, tie rule (power 1e-9, alpha index, subset). selftest() in native18.py verifies
 * that the DCS and PBS decisions of this file equal those of screen_core.c.
 *
 * Policies (argument `policy`):
 *   0 DCS      descending-cardinality search, no screening                         (exact)
 *   1 PBS      DCS + robust pre-beam bound per subset                              (exact)
 *   3 CBD      DCS started at the cardinality bound s_bar of the Corollary          (exact)
 *   4 CBPBS    CBD + pre-beam bound per subset                                     (exact)
 *   5 ACS      ascending cardinality 1..s_bar, every level evaluated               (exact)
 *   6 ACSSTOP  ascending cardinality, stop at the first level without a feasible candidate   (heuristic)
 *   7 GREEDY   add one user at a time (best feasible candidate over all beam rules), stop when none fits (heuristic)
 * Routed: search_routed() computes the noise-limited load eta, looks up the policy-map bit of its bin and runs
 * `route_policy` (1 = PBS in the paper) or DCS.
 *
 * Cardinality bound (Corollary): with per-user loads l_k = gamma N0 / ((||h_k|| - r_k)_+^2 Pmax) sorted ascending,
 * every subset of size s has load >= l_(1) + ... + l_(s); if this exceeds 1 (+ guard), Proposition 3 rejects every
 * subset of size s, so the admitted cardinality is at most s_bar = max{s : l_(1)+...+l_(s) <= 1 + guard}.
 * The same fail-open rules as early_reject() are applied (a user with |rel| <= guard makes s_bar = K).
 *
 * Stage timing: compile with -DSTAGE_TIMING. Stages: 0 load/norms/bound setup, 1 pre-beam bound, 2 beam
 * generation (Gram, inverse, W), 3 robust coefficients (gains, a, F, u), 4 coupling test, 5 power solve,
 * 6 selection and bookkeeping (total minus the other stages is computed in Python from the outer timer).
 * Timer calls cost time; the untimed library is used for all runtime endpoints, the timed one only for shares.
 */
#include <math.h>
#include <string.h>

#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

#define KMAX 16
#define MMAX 256
#define LMAX 16
#define CANDMAX 4096
#define NSTAGE 8

#ifdef STAGE_TIMING
#if defined(_WIN32)
#include <windows.h>
static double now_ms(void) { static LARGE_INTEGER f; LARGE_INTEGER t; if (!f.QuadPart) QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t); return 1e3 * (double)t.QuadPart / (double)f.QuadPart; }
#else
#include <time.h>
static double now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return 1e3 * (double)t.tv_sec + 1e-6 * (double)t.tv_nsec; }
#endif
static double ST[NSTAGE]; static long SC[NSTAGE];
#define TDECL int _stg = -1; double _ts = 0.0;
#define ENTER(s) do { double _t = now_ms(); if (_stg >= 0) ST[_stg] += _t - _ts; _ts = _t; _stg = (s); SC[s]++; } while (0)
#define LEAVE() do { if (_stg >= 0) ST[_stg] += now_ms() - _ts; _stg = -1; } while (0)
#define RET(x) do { LEAVE(); return (x); } while (0)
EXPORT int stage_timing_enabled(void) { return 1; }
EXPORT void stage_reset(void) { int i; for (i = 0; i < NSTAGE; i++) { ST[i] = 0.0; SC[i] = 0; } }
EXPORT void stage_read(double *t, long *c) { int i; for (i = 0; i < NSTAGE; i++) { t[i] = ST[i]; c[i] = SC[i]; } }
EXPORT double timer_pair_cost_ms(int n) { int i; double t0 = now_ms(), s = 0.0; for (i = 0; i < n; i++) { double a = now_ms(); s += now_ms() - a; } (void)s; return (now_ms() - t0) / n; }
#else
#define TDECL
#define ENTER(s) do { } while (0)
#define LEAVE() do { } while (0)
#define RET(x) return (x)
EXPORT int stage_timing_enabled(void) { return 0; }
EXPORT void stage_reset(void) { }
EXPORT void stage_read(double *t, long *c) { int i; for (i = 0; i < NSTAGE; i++) { t[i] = 0.0; c[i] = 0; } }
EXPORT double timer_pair_cost_ms(int n) { (void)n; return 0.0; }
#endif

typedef struct { double re, im; } cplx;
static cplx cmul(cplx a, cplx b) { cplx c; c.re = a.re * b.re - a.im * b.im; c.im = a.re * b.im + a.im * b.re; return c; }
static cplx cconjmul(cplx a, cplx b) { cplx c; c.re = a.re * b.re + a.im * b.im; c.im = a.re * b.im - a.im * b.re; return c; }
static cplx cdiv(cplx a, cplx b) { double d = b.re * b.re + b.im * b.im; cplx c; c.re = (a.re * b.re + a.im * b.im) / d; c.im = (a.im * b.re - a.re * b.im) / d; return c; }
static double cabs2(cplx a) { return a.re * a.re + a.im * a.im; }

enum { ST_FEASIBLE = 0, ST_BEAM = 1, ST_ZERO = 2, ST_COUPLING = 3, ST_INVALID = 4, ST_POWER = 5 };

/* status counters per candidate class: [0] feasible [1] beam [2] zero gain [3] coupling [4] invalid [5] power */
static long CLS[6];

static int eval_candidate(const double *Hre, const double *Him, int M, const int *idx, int S, double alpha,
                          double q, double sigma, double gamma, double noise, double pmax, double *power)
{
    cplx G[KMAX][KMAX], X[KMAX][2 * KMAX];
    static cplx W[MMAX * KMAX];
    double nrm[KMAX], r[KMAX], g[KMAX][KMAX], a[KMAX], F[KMAX][KMAX], u[KMAX], A[KMAX][KMAX], b[KMAX], p[KMAX];
    int i, j, k, m, piv;
    double tr = 0.0, scale, tol;
    TDECL
    ENTER(2);
    for (i = 0; i < S; i++) {
        const double *hr = Hre + (size_t)idx[i] * M, *hi = Him + (size_t)idx[i] * M;
        double s2 = 0.0;
        for (m = 0; m < M; m++) s2 += hr[m] * hr[m] + hi[m] * hi[m];
        nrm[i] = sqrt(s2);
    }
    for (i = 0; i < S; i++)
        for (j = 0; j < S; j++) {
            const double *ar = Hre + (size_t)idx[i] * M, *ai = Him + (size_t)idx[i] * M;
            const double *br = Hre + (size_t)idx[j] * M, *bi = Him + (size_t)idx[j] * M;
            cplx acc = {0.0, 0.0};
            for (m = 0; m < M; m++) { acc.re += ar[m] * br[m] + ai[m] * bi[m]; acc.im += ar[m] * bi[m] - ai[m] * br[m]; }
            G[i][j] = acc;
        }
    for (i = 0; i < S; i++) tr += G[i][i].re;
    scale = tr / S; if (scale < 1e-30) scale = 1e-30;
    for (i = 0; i < S; i++) {
        for (j = 0; j < S; j++) { X[i][j] = G[i][j]; X[i][S + j].re = (i == j); X[i][S + j].im = 0.0; }
        X[i][i].re += alpha * scale;
    }
    tol = (alpha == 0.0) ? 1e-26 * (tr > 0 ? tr : 1.0) : 0.0;
    for (k = 0; k < S; k++) {
        double best = -1.0; piv = k;
        for (i = k; i < S; i++) { double v = cabs2(X[i][k]); if (v > best) { best = v; piv = i; } }
        if (best <= tol * tol || best == 0.0) RET(ST_BEAM);
        if (piv != k) for (j = 0; j < 2 * S; j++) { cplx t = X[k][j]; X[k][j] = X[piv][j]; X[piv][j] = t; }
        {
            cplx d = X[k][k];
            for (j = 0; j < 2 * S; j++) X[k][j] = cdiv(X[k][j], d);
            for (i = 0; i < S; i++) if (i != k) {
                cplx f = X[i][k];
                if (f.re != 0.0 || f.im != 0.0) for (j = 0; j < 2 * S; j++) { cplx t = cmul(f, X[k][j]); X[i][j].re -= t.re; X[i][j].im -= t.im; }
            }
        }
    }
    for (j = 0; j < S; j++) {
        double cn = 0.0;
        for (m = 0; m < M; m++) {
            cplx acc = {0.0, 0.0};
            for (i = 0; i < S; i++) {
                cplx h; h.re = Hre[(size_t)idx[i] * M + m]; h.im = Him[(size_t)idx[i] * M + m];
                cplx t = cmul(h, X[i][S + j]); acc.re += t.re; acc.im += t.im;
            }
            W[(size_t)j * M + m] = acc; cn += cabs2(acc);
        }
        cn = sqrt(cn);
        if (cn <= 1e-30) RET(ST_BEAM);
        for (m = 0; m < M; m++) { W[(size_t)j * M + m].re /= cn; W[(size_t)j * M + m].im /= cn; }
    }
    ENTER(3);
    for (k = 0; k < S; k++) {
        r[k] = q * sigma * nrm[k] / sqrt((double)M);
        for (j = 0; j < S; j++) {
            cplx acc = {0.0, 0.0};
            for (m = 0; m < M; m++) {
                cplx h; h.re = Hre[(size_t)idx[k] * M + m]; h.im = Him[(size_t)idx[k] * M + m];
                cplx t = cconjmul(h, W[(size_t)j * M + m]); acc.re += t.re; acc.im += t.im;
            }
            g[k][j] = sqrt(cabs2(acc));
        }
        { double d = g[k][k] - r[k]; a[k] = d > 0 ? d * d : 0.0; }
        if (a[k] <= 0.0) RET(ST_ZERO);
    }
    for (k = 0; k < S; k++) {
        for (j = 0; j < S; j++) { double t = g[k][j] + r[k]; F[k][j] = (k == j) ? 0.0 : gamma * t * t / a[k]; }
        u[k] = gamma * noise / a[k];
    }
    ENTER(4);
    {
        double c = 1.0 / (1.0 - 1e-10);
        for (i = 0; i < S; i++) for (j = 0; j < S; j++) A[i][j] = (i == j) - c * F[i][j];
        for (k = 0; k < S; k++) {
            if (!(A[k][k] > 0.0)) RET(ST_COUPLING);
            for (i = k + 1; i < S; i++) { double f = A[i][k] / A[k][k]; if (f != 0.0) for (j = k; j < S; j++) A[i][j] -= f * A[k][j]; }
        }
    }
    ENTER(5);
    for (i = 0; i < S; i++) { for (j = 0; j < S; j++) A[i][j] = (i == j) - F[i][j]; b[i] = u[i]; }
    for (k = 0; k < S; k++) {
        if (!(A[k][k] > 0.0)) RET(ST_COUPLING);
        for (i = k + 1; i < S; i++) { double f = A[i][k] / A[k][k]; if (f != 0.0) { for (j = k; j < S; j++) A[i][j] -= f * A[k][j]; b[i] -= f * b[k]; } }
    }
    {
        double tot = 0.0;
        for (i = S - 1; i >= 0; i--) { double s = b[i]; for (j = i + 1; j < S; j++) s -= A[i][j] * p[j]; p[i] = s / A[i][i]; }
        for (i = 0; i < S; i++) { if (!(p[i] >= 0.0) || !isfinite(p[i])) RET(ST_INVALID); tot += p[i]; }
        *power = tot;
        if (tot > pmax * (1.0 + 1e-9)) RET(ST_POWER);
    }
    RET(ST_FEASIBLE);
}

static int eval_counted(const double *Hre, const double *Him, int M, const int *idx, int S, double alpha,
                        double q, double sigma, double gamma, double noise, double pmax, double *power)
{
    int st = eval_candidate(Hre, Him, M, idx, S, alpha, q, sigma, gamma, noise, pmax, power);
    CLS[st]++;
    return st;
}

/* robust pre-beam bound, identical to screen_core.c */
static int early_reject(const double *nrm, const int *idx, int S, int M, double q, double sigma, double gamma,
                        double noise, double pmax, double guard)
{
    int i; double lb = 0.0;
    TDECL
    ENTER(1);
    for (i = 0; i < S; i++) {
        double n = nrm[idx[i]], r = q * sigma * n / sqrt((double)M), rel = (n - r) / (n > 1e-300 ? n : 1e-300), sq;
        if (rel < -guard) RET(1);
        if (fabs(rel) <= guard) RET(0);
        sq = (n - r) * (n - r);
        if (sq <= 1e-25) RET(0);
        lb += gamma * noise / sq;
    }
    {
        double ex = lb / pmax - 1.0;
        if (!isfinite(ex)) RET(0);
        RET(ex > guard);
    }
}

/* cardinality bound s_bar of the Corollary (same fail-open rules as early_reject) */
static int card_bound(const double *nrm, int K, int M, double q, double sigma, double gamma, double noise, double pmax, double guard)
{
    double l[KMAX], cum = 0.0; int k, i, j, s = 0;
    for (k = 0; k < K; k++) {
        double n = nrm[k], r = q * sigma * n / sqrt((double)M), rel = (n - r) / (n > 1e-300 ? n : 1e-300), sq;
        if (rel < -guard) { l[k] = HUGE_VAL; continue; }
        if (fabs(rel) <= guard) return K;              /* a fail-open user: subsets containing it are never rejected */
        sq = (n - r) * (n - r);
        if (sq <= 1e-25) return K;
        l[k] = gamma * noise / sq / pmax;
    }
    for (i = 1; i < K; i++) { double v = l[i]; j = i - 1; while (j >= 0 && l[j] > v) { l[j + 1] = l[j]; j--; } l[j + 1] = v; }
    for (k = 0; k < K; k++) {
        if (!isfinite(l[k])) break;                    /* zero-gain users: every subset containing one is rejected */
        cum += l[k];
        if (!isfinite(cum)) return K;                  /* early_reject fails open on a non-finite sum */
        if (cum - 1.0 > guard) break;   /* early_reject uses lb/pmax - 1 > guard; here l already divided by pmax */
        s = k + 1;
    }
    return s;
}

EXPORT int cardinality_bound(const double *Hre, const double *Him, int M, int K, double q, double sigma, double gamma,
                             double noise, double pmax, double guard)
{
    double nrm[KMAX]; int k, m;
    for (k = 0; k < K; k++) { double s2 = 0.0; for (m = 0; m < M; m++) s2 += Hre[(size_t)k * M + m] * Hre[(size_t)k * M + m] + Him[(size_t)k * M + m] * Him[(size_t)k * M + m]; nrm[k] = sqrt(s2); }
    return card_bound(nrm, K, M, q, sigma, gamma, noise, pmax, guard);
}

EXPORT double early_ratio(const double *Hre, const double *Him, int M, int K, double q, double sigma, double gamma,
                          double noise, double pmax)
{
    int k, m; double s = 0.0;
    for (k = 0; k < K; k++) {
        double n2 = 0.0, n, r, g;
        for (m = 0; m < M; m++) n2 += Hre[(size_t)k * M + m] * Hre[(size_t)k * M + m] + Him[(size_t)k * M + m] * Him[(size_t)k * M + m];
        n = sqrt(n2); r = q * sigma * n / sqrt((double)M); g = (n - r) > 0 ? (n - r) * (n - r) : 0.0;
        if (g <= 1e-300) return 1e12;
        s += gamma * noise / g;
    }
    s /= pmax;
    return s < 1e12 ? s : 1e12;
}

static int next_comb(int *c, int S, int K)
{
    int i = S - 1;
    while (i >= 0 && c[i] == K - S + i) i--;
    if (i < 0) return 0;
    c[i]++;
    for (i = i + 1; i < S; i++) c[i] = c[i - 1] + 1;
    return 1;
}

static int lex_less(const int *x, const int *y, int S) { int i; for (i = 0; i < S; i++) { if (x[i] != y[i]) return x[i] < y[i]; } return 0; }

static int cs[CANDMAX][KMAX]; static int ca[CANDMAX]; static double cp[CANDMAX];

/* tie rule of the paper among nf feasible candidates of one size; returns index */
static int select_best(int nf, int size)
{
    double pmin = cp[0]; int i, best = -1;
    for (i = 1; i < nf; i++) if (cp[i] < pmin) pmin = cp[i];
    for (i = 0; i < nf; i++) {
        if (cp[i] > pmin * (1.0 + 1e-9)) continue;
        if (best < 0 || ca[i] < ca[best] || (ca[i] == ca[best] && lex_less(cs[i], cs[best], size))) best = i;
    }
    return best;
}

/* evaluate every subset of `size` (with optional pre-beam bound); returns number of feasible candidates (stored) or -2 */
static int eval_level(const double *Hre, const double *Him, const double *nrm, int M, int K, int size, const double *alphas, int L,
                      double q, double sigma, double gamma, double noise, double pmax, double guard, int use_bound, long *counters)
{
    int c[KMAX], nf = 0, more = 1, i;
    for (i = 0; i < size; i++) c[i] = i;
    while (more) {
        int l;
        counters[3]++;
        if (use_bound && early_reject(nrm, c, size, M, q, sigma, gamma, noise, pmax, guard)) {
            counters[1] += L; counters[2] += L; counters[4 + size]++;
        } else {
            for (l = 0; l < L; l++) {
                double pw = 0.0; int st;
                counters[2]++; counters[0]++;
                st = eval_counted(Hre, Him, M, c, size, alphas[l], q, sigma, gamma, noise, pmax, &pw);
                if (st == ST_FEASIBLE) {
                    if (nf >= CANDMAX) return -2;
                    memcpy(cs[nf], c, sizeof(int) * size); ca[nf] = l; cp[nf] = pw; nf++;
                }
            }
        }
        more = next_comb(c, size, K);
    }
    return nf;
}

/*
 * counters layout (length 4 + KMAX + 1 + 8 = 29):
 *   [0] full candidate evaluations  [1] candidates rejected before beam  [2] candidates seen  [3] subsets visited
 *   [4 + s] subsets of size s rejected before beam (s = 1..K)
 *   [21] s_bar  [22] levels evaluated  [23..28] candidate classes: feasible, beam, zero gain, coupling, invalid, power
 */
#define NCNT 29
EXPORT int search18(const double *Hre, const double *Him, int M, int K, const double *alphas, int L,
                    double q, double sigma, double gamma, double noise, double pmax, double guard, int policy,
                    int *out_subset, int *out_alpha_index, double *out_power, int *out_card, long *counters)
{
    double nrm[KMAX];
    int size, k, m, i, sbar, nf, best;
    TDECL
    if (K > KMAX || M > MMAX || L > LMAX) return -1;
    for (i = 0; i < NCNT; i++) counters[i] = 0;
    for (i = 0; i < 6; i++) CLS[i] = 0;
    ENTER(0);
    for (k = 0; k < K; k++) { double s2 = 0.0; for (m = 0; m < M; m++) s2 += Hre[(size_t)k * M + m] * Hre[(size_t)k * M + m] + Him[(size_t)k * M + m] * Him[(size_t)k * M + m]; nrm[k] = sqrt(s2); }
    sbar = (policy == 3 || policy == 4 || policy == 5) ? card_bound(nrm, K, M, q, sigma, gamma, noise, pmax, guard) : K;
    counters[21] = sbar;
    *out_card = 0;
    ENTER(6);
    if (policy == 0 || policy == 1 || policy == 3 || policy == 4) {                 /* descending */
        int use_bound = (policy == 1 || policy == 4);
        for (size = sbar; size >= 1; size--) {
            LEAVE();
            nf = eval_level(Hre, Him, nrm, M, K, size, alphas, L, q, sigma, gamma, noise, pmax, guard, use_bound, counters);
            ENTER(6);
            counters[22]++;
            if (nf == -2) RET(-2);
            if (nf > 0) {
                best = select_best(nf, size);
                memcpy(out_subset, cs[best], sizeof(int) * size);
                *out_alpha_index = ca[best]; *out_power = cp[best]; *out_card = size;
                break;
            }
        }
    } else if (policy == 5 || policy == 6) {                                         /* ascending */
        int top = (policy == 5) ? sbar : K;
        for (size = 1; size <= top; size++) {
            LEAVE();
            nf = eval_level(Hre, Him, nrm, M, K, size, alphas, L, q, sigma, gamma, noise, pmax, guard, 0, counters);
            ENTER(6);
            counters[22]++;
            if (nf == -2) RET(-2);
            if (nf > 0) {
                best = select_best(nf, size);
                memcpy(out_subset, cs[best], sizeof(int) * size);
                *out_alpha_index = ca[best]; *out_power = cp[best]; *out_card = size;
            } else if (policy == 6) break;
        }
    } else if (policy == 7) {                                                        /* greedy */
        int cur[KMAX], ncur = 0, in[KMAX];
        for (k = 0; k < K; k++) in[k] = 0;
        while (ncur < K) {
            int bestk = -1, bestl = -1, cand[KMAX], bsub[KMAX]; double bestp = 0.0;
            counters[22]++;
            for (k = 0; k < K; k++) {
                int l, t = 0, j;
                if (in[k]) continue;
                for (j = 0; j < ncur; j++) if (cur[j] < k) cand[t++] = cur[j];
                cand[t++] = k;
                for (j = 0; j < ncur; j++) if (cur[j] > k) cand[t++] = cur[j];
                counters[3]++;
                for (l = 0; l < L; l++) {
                    double pw = 0.0; int st;
                    counters[2]++; counters[0]++;
                    LEAVE();
                    st = eval_counted(Hre, Him, M, cand, ncur + 1, alphas[l], q, sigma, gamma, noise, pmax, &pw);
                    ENTER(6);
                    if (st != ST_FEASIBLE) continue;
                    if (bestk < 0 || pw < bestp * (1.0 - 1e-9) ||
                        (pw <= bestp * (1.0 + 1e-9) && (l < bestl || (l == bestl && lex_less(cand, bsub, ncur + 1))))) {
                        bestk = k; bestl = l; bestp = pw; memcpy(bsub, cand, sizeof(int) * (ncur + 1));
                    }
                }
            }
            if (bestk < 0) break;
            memcpy(cur, bsub, sizeof(int) * (ncur + 1)); ncur++; in[bestk] = 1;
            memcpy(out_subset, cur, sizeof(int) * ncur); *out_alpha_index = bestl; *out_power = bestp; *out_card = ncur;
        }
    } else RET(-3);
    for (i = 0; i < 6; i++) counters[23 + i] = CLS[i];
    RET(0);
}

EXPORT int search18_routed(const double *Hre, const double *Him, int M, int K, const double *alphas, int L,
                           double q, double sigma, double gamma, double noise, double pmax, double guard,
                           const double *bins, int nbins, int active_mask, int route_policy,
                           int *out_subset, int *out_alpha_index, double *out_power, int *out_card, long *counters, int *out_policy)
{
    double er; int j = 0, b;
    TDECL
    ENTER(0);
    er = early_ratio(Hre, Him, M, K, q, sigma, gamma, noise, pmax);
    for (b = 0; b < nbins; b++) if (er >= bins[b]) j++;
    *out_policy = ((active_mask >> j) & 1) ? route_policy : 0;
    LEAVE();
    return search18(Hre, Him, M, K, alphas, L, q, sigma, gamma, noise, pmax, guard, *out_policy,
                    out_subset, out_alpha_index, out_power, out_card, counters);
}

/* run n times inside C; policy < 0 means routed with route_policy = -policy */
EXPORT int repeat18(int n, int policy, const double *Hre, const double *Him, int M, int K, const double *alphas, int L,
                    double q, double sigma, double gamma, double noise, double pmax, double guard,
                    const double *bins, int nbins, int active_mask,
                    int *out_subset, int *out_alpha_index, double *out_power, int *out_card, long *counters, int *out_policy)
{
    int i, st = 0;
    for (i = 0; i < n; i++) {
        if (policy < 0) st = search18_routed(Hre, Him, M, K, alphas, L, q, sigma, gamma, noise, pmax, guard, bins, nbins, active_mask, -policy,
                                             out_subset, out_alpha_index, out_power, out_card, counters, out_policy);
        else { st = search18(Hre, Him, M, K, alphas, L, q, sigma, gamma, noise, pmax, guard, policy, out_subset, out_alpha_index, out_power, out_card, counters); *out_policy = policy; }
        if (st != 0) return st;
    }
    return st;
}

/* ---- micro-benchmarks for per-operation costs (hardware study) ---- */
/* evaluate one candidate n times; returns its status (0 feasible ... 5 power) */
EXPORT int bench_candidate(int n, const double *Hre, const double *Him, int M, const int *idx, int S, double alpha,
                           double q, double sigma, double gamma, double noise, double pmax, double *power)
{
    int i, st = 0;
    for (i = 0; i < n; i++) st = eval_candidate(Hre, Him, M, idx, S, alpha, q, sigma, gamma, noise, pmax, power);
    return st;
}

/* evaluate the pre-beam bound of one subset n times (norms computed once outside the loop); returns 1 if rejected */
EXPORT int bench_bound(int n, const double *Hre, const double *Him, int M, int K, const int *idx, int S,
                       double q, double sigma, double gamma, double noise, double pmax, double guard)
{
    double nrm[KMAX]; int i, k, m, st = 0;
    for (k = 0; k < K; k++) { double s2 = 0.0; for (m = 0; m < M; m++) s2 += Hre[(size_t)k * M + m] * Hre[(size_t)k * M + m] + Him[(size_t)k * M + m] * Him[(size_t)k * M + m]; nrm[k] = sqrt(s2); }
    for (i = 0; i < n; i++) st = early_reject(nrm, idx, S, M, q, sigma, gamma, noise, pmax, guard);
    return st;
}

/* compute the noise-limited load n times (routing cost T_load) */
EXPORT double bench_load(int n, const double *Hre, const double *Him, int M, int K, double q, double sigma, double gamma, double noise, double pmax)
{
    int i; double s = 0.0;
    for (i = 0; i < n; i++) s += early_ratio(Hre, Him, M, K, q, sigma, gamma, noise, pmax);
    return s / (n > 0 ? n : 1);
}
