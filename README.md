A collection of verification and validation suites for [MC/DC](https://github.com/mcdc-project/mcdc).

# Verification

## Analytical Verification

### Neutron transport

#### [Suite A](https://github.com/mcdc-project/mcdc-vv/tree/master/verification/analytical/neutron/suite_A) - Analytical multigroup fixed-source

Verification includes observing the $`N^{-0.5}`$ convergence in the errors (against analytical solutions) as the number of source particles $`N`$ is increased.
The problems include:
- Steady-state flux distribution of a purely-absorbing multi-layer slab system
- Reed's classic 1D problem [[reference](https://www.tandfonline.com/doi/abs/10.13182/NSE46-309)]
- Flux temporal propagation from an isotropic planar surface source
- Variations of the AZURV1 transient benchmark [[reference](https://www.osti.gov/servlets/purl/975281)]
- Spectrum temporal evolutions from pulsed homogeneous infinite SHEM361-group thermal systems
    
## Benchmark verification (Code-to-code comparison)

More involved problems that have no analytical solution are considered.
MC/DC results are compared to those of [OpenMC](https://github.com/openmc-dev/openmc)) (input scripts provided).

### Neutron transport

#### [Multigroup](https://github.com/mcdc/mcdc-vv/tree/master/verification/benchmark/neutron/multigroup)
    
Verification includes observing the $`N^{-0.5}`$ convergence in the relative differences of the two codes as the number of source particles $`N`$ is increased.
The problems include:
- Time-dependent version of the Kobayashi Dog-Leg transport benchmark [[Zenodo link](https://zenodo.org/records/15069882)]
- Four-phase C5G7 transient benchmark [[Zenodo link](https://zenodo.org/records/15719118)]

#### [Continuous energy](https://github.com/mcdc-project/mcdc-vv/tree/master/verification/benchmark/neutron/continuous_energy)

Verification includes observing the agreement in the results of the two codes.
The problems include:
- Temporal spectrum evolutions of neutron-pulsed pincells with various materials:
  - UO2 and Water
  - UO2 and Helium
