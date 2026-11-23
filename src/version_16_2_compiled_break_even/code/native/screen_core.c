/*
 * screen_core.c -- compiled cardinality-ordered search (CARD) and pre-beam screening (EARLY)
 * for the fixed-beam robust SINR model of robust_model.solve (V15.2).
 *
 * Mirrors the Python reference:
 *   beam      : ZF (alpha = 0, rank check) or RZF W = H (H^H H + alpha*tr(H^H H)/S I)^{-1}, unit-norm columns
 *   robust    : r_k = q*sigma*||h_k||/sqrt(M); a_k = (|h_k^H w_k| - r_k)_+^2; F_kj = gamma (|h_k^H w_j| + r_k)^2 / a_k; u_k = gamma N0 / a_k
 *   coupling  : rho(F) >= 1 - 1e-10  <=>  I - F/(1 - 1e-10) is NOT a nonsingular M-matrix (pivot test, exact for F >= 0)
 *   power     : p = (I - F)^{-1} u, feasible iff p >= 0 finite and sum(p) <= Pmax (1 + 1e-9)
 *   EARLY     : robust pre-beam bound sum_k gamma N0 / (||h_k|| - r_k)^2 > Pmax (1 + guard) rejects all beams of a subset
 *   decision  : max cardinality; min power with relative ties <= 1e-9; smaller alpha index; lexicographically smaller subset
 * The LP audit of the Python solver is NOT performed (it verifies p*, it does not change the decision).
 * Plain C89/C99 with manual complex arithmetic so that gcc, clang, MinGW and MSVC all compile it.
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

typedef struct { double re, im; } cplx;
static cplx cmul(cplx a, cplx b) { cplx c; c.re = a.re * b.re - a.im * b.im; c.im = a.re * b.im + a.im * b.re; return c; }
static cplx cconjmul(cplx a, cplx b) { cplx c; c.re = a.re * b.re + a.im * b.im; c.im = a.re * b.im - a.im * b.re; return c; } /* conj(a)*b */
static cplx cdiv(cplx a, cplx b) { double d = b.re * b.re + b.im * b.im; cplx c; c.re = (a.re * b.re + a.im * b.im) / d; c.im = (a.im * b.re - a.re * b.im) / d; return c; }
static double cabs2(cplx a) { return a.re * a.re + a.im * a.im; }

enum { ST_FEASIBLE = 0, ST_BEAM = 1, ST_ZERO = 2, ST_COUPLING = 3, ST_INVALID = 4, ST_POWER = 5 };

/* Evaluate one candidate: users idx[0..S-1], regularization alpha. Returns status, writes total power. */
static int eval_candidate(const double *Hre, const double *Him, int M, const int *idx, int S, double alpha,
                          double q, double sigma, double gamma, double noise, double pmax, double *power)
{
    cplx G[KMAX][KMAX], X[KMAX][2 * KMAX];
    static cplx W[MMAX * KMAX];
    double nrm[KMAX], r[KMAX], g[KMAX][KMAX], a[KMAX], F[KMAX][KMAX], u[KMAX], A[KMAX][KMAX], b[KMAX], p[KMAX];
    int i, j, k, m, piv;
    double tr = 0.0, scale, tol;
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
    /* X = [A | I], A = G + alpha*scale*I ; Gauss-Jordan with partial pivoting */
    for (i = 0; i < S; i++) {
        for (j = 0; j < S; j++) { X[i][j] = G[i][j]; X[i][S + j].re = (i == j); X[i][S + j].im = 0.0; }
        X[i][i].re += alpha * scale;
    }
    tol = (alpha == 0.0) ? 1e-26 * (tr > 0 ? tr : 1.0) : 0.0;   /* ZF rank check, mirrors matrix_rank on H */
    for (k = 0; k < S; k++) {
        double best = -1.0; piv = k;
        for (i = k; i < S; i++) { double v = cabs2(X[i][k]); if (v > best) { best = v; piv = i; } }
        if (best <= tol * tol || best == 0.0) return ST_BEAM;
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
    /* W = H_S * Ainv (M x S), columns normalized */
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
        if (cn <= 1e-30) return ST_BEAM;
        for (m = 0; m < M; m++) { W[(size_t)j * M + m].re /= cn; W[(size_t)j * M + m].im /= cn; }
    }
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
        if (a[k] <= 0.0) return ST_ZERO;
    }
    for (k = 0; k < S; k++) {
        for (j = 0; j < S; j++) { double t = g[k][j] + r[k]; F[k][j] = (k == j) ? 0.0 : gamma * t * t / a[k]; }
        u[k] = gamma * noise / a[k];
    }
    /* coupling test: I - F/(1-1e-10) must be a nonsingular M-matrix (all pivots > 0, no pivoting) */
    {
        double c = 1.0 / (1.0 - 1e-10);
        for (i = 0; i < S; i++) for (j = 0; j < S; j++) A[i][j] = (i == j) - c * F[i][j];
        for (k = 0; k < S; k++) {
            if (!(A[k][k] > 0.0)) return ST_COUPLING;
            for (i = k + 1; i < S; i++) { double f = A[i][k] / A[k][k]; if (f != 0.0) for (j = k; j < S; j++) A[i][j] -= f * A[k][j]; }
        }
    }
    /* p = (I - F)^{-1} u */
    for (i = 0; i < S; i++) { for (j = 0; j < S; j++) A[i][j] = (i == j) - F[i][j]; b[i] = u[i]; }
    for (k = 0; k < S; k++) {
        if (!(A[k][k] > 0.0)) return ST_COUPLING;
        for (i = k + 1; i < S; i++) { double f = A[i][k] / A[k][k]; if (f != 0.0) { for (j = k; j < S; j++) A[i][j] -= f * A[k][j]; b[i] -= f * b[k]; } }
    }
    {
        double tot = 0.0;
        for (i = S - 1; i >= 0; i--) { double s = b[i]; for (j = i + 1; j < S; j++) s -= A[i][j] * p[j]; p[i] = s / A[i][i]; }
        for (i = 0; i < S; i++) { if (!(p[i] >= 0.0) || !isfinite(p[i])) return ST_INVALID; tot += p[i]; }
        *power = tot;
        if (tot > pmax * (1.0 + 1e-9)) return ST_POWER;
    }
    return ST_FEASIBLE;
}

/* Robust pre-beam bound. Returns 1 if the subset is certified infeasible. */
static int early_reject(const double *nrm, const int *idx, int S, int M, double q, double sigma, double gamma,
                        double noise, double pmax, double guard)
{
    int i; double lb = 0.0;
    for (i = 0; i < S; i++) {
        double n = nrm[idx[i]], r = q * sigma * n / sqrt((double)M), rel = (n - r) / (n > 1e-300 ? n : 1e-300), sq;
        if (rel < -guard) return 1;              /* zero robust gain for every beam */
        if (fabs(rel) <= guard) return 0;        /* uncertain: fail open */
        sq = (n - r) * (n - r);
        if (sq <= 1e-25) return 0;
        lb += gamma * noise / sq;
    }
    {
        double ex = lb / pmax - 1.0;
        if (!isfinite(ex)) return 0;
        return ex > guard;                        /* |ex| <= guard: fail open */
    }
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

/* next combination of size S from {0..K-1} in lexicographic order; returns 0 when exhausted */
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

/*
 * search: policy 0 = CARD, 1 = EARLY (robust pre-beam bound).
 * H given user-major: Hre[k*M + m]. Outputs:
 *   out_subset[0..card-1], out_alpha_index, out_power, out_card (0 if nothing feasible)
 *   counters[0] full candidate evaluations, [1] candidates rejected before beam, [2] candidates seen,
 *   counters[3] subsets visited, counters[4 + s] subsets of size s rejected before beam (s = 1..K)
 */
EXPORT int search(const double *Hre, const double *Him, int M, int K, const double *alphas, int L,
                  double q, double sigma, double gamma, double noise, double pmax, double guard, int policy,
                  int *out_subset, int *out_alpha_index, double *out_power, int *out_card, long *counters)
{
    static int cs[CANDMAX][KMAX]; static int ca[CANDMAX]; static double cp[CANDMAX];
    double nrm[KMAX];
    int size, k, m, i;
    if (K > KMAX || M > MMAX || L > LMAX) return -1;
    for (i = 0; i < 4 + KMAX + 1; i++) counters[i] = 0;
    for (k = 0; k < K; k++) { double s2 = 0.0; for (m = 0; m < M; m++) s2 += Hre[(size_t)k * M + m] * Hre[(size_t)k * M + m] + Him[(size_t)k * M + m] * Him[(size_t)k * M + m]; nrm[k] = sqrt(s2); }
    *out_card = 0;
    for (size = K; size >= 1; size--) {
        int c[KMAX], nf = 0, more = 1;
        for (i = 0; i < size; i++) c[i] = i;
        while (more) {
            int l;
            counters[3]++;
            if (policy == 1 && early_reject(nrm, c, size, M, q, sigma, gamma, noise, pmax, guard)) {
                counters[1] += L; counters[2] += L; counters[4 + size]++;
            } else {
                for (l = 0; l < L; l++) {
                    double pw = 0.0; int st;
                    counters[2]++; counters[0]++;
                    st = eval_candidate(Hre, Him, M, c, size, alphas[l], q, sigma, gamma, noise, pmax, &pw);
                    if (st == ST_FEASIBLE) {
                        if (nf >= CANDMAX) return -2;
                        memcpy(cs[nf], c, sizeof(int) * size); ca[nf] = l; cp[nf] = pw; nf++;
                    }
                }
            }
            more = next_comb(c, size, K);
        }
        if (nf > 0) {
            double pmin = cp[0]; int best = -1;
            for (i = 1; i < nf; i++) if (cp[i] < pmin) pmin = cp[i];
            for (i = 0; i < nf; i++) {
                if (cp[i] > pmin * (1.0 + 1e-9)) continue;
                if (best < 0 || ca[i] < ca[best] || (ca[i] == ca[best] && lex_less(cs[i], cs[best], size))) best = i;
            }
            memcpy(out_subset, cs[best], sizeof(int) * size);
            *out_alpha_index = ca[best]; *out_power = cp[best]; *out_card = size;
            return 0;
        }
    }
    return 0;
}

/*
 * search_routed: compiled ROUTED policy. Computes the early ratio, maps it to the locked cell
 * ER{j} (j = number of bin edges <= early ratio), and runs EARLY if bit j of active_mask is set
 * (cell locked to a non-CARD policy for this K, L), otherwise CARD. *out_policy returns 0/1.
 */
EXPORT int search_routed(const double *Hre, const double *Him, int M, int K, const double *alphas, int L,
                         double q, double sigma, double gamma, double noise, double pmax, double guard,
                         const double *bins, int nbins, int active_mask,
                         int *out_subset, int *out_alpha_index, double *out_power, int *out_card, long *counters, int *out_policy)
{
    double er = early_ratio(Hre, Him, M, K, q, sigma, gamma, noise, pmax);
    int j = 0, b;
    for (b = 0; b < nbins; b++) if (er >= bins[b]) j++;
    *out_policy = (active_mask >> j) & 1;
    return search(Hre, Him, M, K, alphas, L, q, sigma, gamma, noise, pmax, guard, *out_policy,
                  out_subset, out_alpha_index, out_power, out_card, counters);
}

/*
 * repeat_search: run the selected policy n times inside C (mode 0 CARD, 1 EARLY, 2 ROUTED) so that the
 * Python/ctypes call overhead is paid once per measurement and is identical for all policies.
 */
EXPORT int repeat_search(int n, int mode, const double *Hre, const double *Him, int M, int K, const double *alphas, int L,
                         double q, double sigma, double gamma, double noise, double pmax, double guard,
                         const double *bins, int nbins, int active_mask,
                         int *out_subset, int *out_alpha_index, double *out_power, int *out_card, long *counters, int *out_policy)
{
    int i, st = 0;
    for (i = 0; i < n; i++) {
        if (mode == 2) st = search_routed(Hre, Him, M, K, alphas, L, q, sigma, gamma, noise, pmax, guard, bins, nbins, active_mask,
                                          out_subset, out_alpha_index, out_power, out_card, counters, out_policy);
        else st = search(Hre, Him, M, K, alphas, L, q, sigma, gamma, noise, pmax, guard, mode,
                         out_subset, out_alpha_index, out_power, out_card, counters);
        if (st != 0) return st;
    }
    return st;
}
