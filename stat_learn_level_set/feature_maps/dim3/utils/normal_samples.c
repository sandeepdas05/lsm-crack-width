#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <math.h>
#include "../../../utils/utils.h"
#include "../../../utils/trilinear.c"

// This utility grabs `nsamples` image samples in both the inward and outward
// normal directions. The sampled points are equally spaced along the normal
// ray, and the ray extends in the inward and outward directions, a
// distance equal to distance from the local spatial coordinate to 
// the provided center of mass (com).

void get_samples(
        int m, int n, int p, double * img, // dims and image vol.
        double * ni, double * nj, double * nk, // unit normal comps
        double   di, double   dj, double   dk, // delta terms
        bool * mask, // boolean mask volume
        double * com, // center of mass (in ? coords)
        int nsamples, // desired # of samples
        double * samples // output volume, shape = (m, n, p, nsamples, 2)
    ) {
    int l,ll;
    double a, b, c;
    double ii_i, jj_i, kk_i;
    double ii_o, jj_o, kk_o;
    bool in_bounds_i, in_bounds_o, is_zero;
    double dt, cdist;

    for (int i=0; i < m; i++) {
        for (int j=0; j < n; j++) {
            for (int k=0; k < p; k++) {
                l = mi3d(i,j,k,m,n,p);
                if (!mask[l]) continue;

                // Distance to center of mass.
                cdist = sqrt(sqr(di*(i-com[0])) +
                             sqr(dj*(j-com[1])) +
                             sqr(dk*(k-com[2])));

                // dt is the step length along in the normal directions.
                dt = cdist / (nsamples+1.0);

                a = dt * ni[l];
                b = dt * nj[l];
                c = dt * nk[l];

                // The gradient vector is zero, so we can't compute
                // the feature for this coordinate, (i,j,k).
                is_zero = (a == 0) && (b == 0) && (c == 0);

                // _i = inward normal
                ii_i = i*di;
                jj_i = j*dj;
                kk_i = k*dk;
                
                // _o = outward normal
                ii_o = i*di;
                jj_o = j*dj;
                kk_o = k*dk;

                for (int q=1; q <= nsamples; q++) {
                    in_bounds_i = check_bounds((int) round(ii_i/di),
                                               (int) round(jj_i/dj),
                                               (int) round(kk_i/dk),
                                               m, n, p);
                    in_bounds_o = check_bounds((int) round(ii_o/di),
                                               (int) round(jj_o/dj),
                                               (int) round(kk_o/dk),
                                               m, n, p);
                    if (!in_bounds_i)
                        printf("i0 %.2f, %.2f, %.2f\n", ii_i, jj_i, kk_i);
//                    else
//                        printf("i1 %.2f, %.2f, %.2f\n", ii_i, jj_i, kk_i);

                    if (!in_bounds_o)
                        printf("o0 %.2f, %.2f, %.2f\n", ii_o, jj_o, kk_o);
//                    else
//                        printf("o1 %.2f, %.2f, %.2f\n", ii_o, jj_o, kk_o);

                    // `samples` is 4D, so we use the map index function `mi3d`
                    // to map the 3D, row-major coordinate to 4D row-major.
                    // `ll` is part of the 4D index computation used below.
                    ll = nsamples*l + q-1;

                    // Add the inward normal sample to `samples`.
                    if (!in_bounds_i || is_zero) {
                        samples[2*ll+0] = 0.0;
                    }
                    else {
                        samples[2*ll+0] = interpolate_point(ii_i, jj_i, kk_i,
                                                            img, 
                                                            di, dj, dk,
                                                            m, n, p);
                    }

                    // Add the outward normal sample to `samples`.
                    if (!in_bounds_o || is_zero) {
                        samples[2*ll+1] = 0.0;
                    }
                    else {
                        samples[2*ll+1] = interpolate_point(ii_o, jj_o, kk_o,
                                                            img,
                                                            di, dj, dk,
                                                            m, n, p);
                    }

                    // Advance one step along ray.
                    ii_i += a;
                    jj_i += b;
                    kk_i += c;

                    ii_o -= a;
                    jj_o -= b;
                    kk_o -= c;
                }

            } // End loop k.
        } // End loop j.
    } // End loop k.
}