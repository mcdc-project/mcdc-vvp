A collection of verification, validation, and performance test suites for [MC/DC](https://github.com/mcdc-project/mcdc).

# Verification

## Analytical Verification

Analytical verification involves observing the $`N^{-0.5}`$ convergence in the errors (against analytical solutions) as the number of source particles $`N`$ is increased.

### Neutron transport

#### [Suite A](https://github.com/mcdc-project/mcdc-vv/tree/master/verification/analytical/neutron/suite_A) - Analytical multigroup fixed-source

- Steady-state flux distribution of a purely-absorbing multi-layer slab system
- Reed's classic 1D problem [[reference](https://www.tandfonline.com/doi/abs/10.13182/NSE46-309)]
- Flux temporal propagation from an isotropic planar surface source
- Variations of the AZURV1 transient benchmark [[reference](https://www.osti.gov/servlets/purl/975281)]
- Spectrum temporal evolutions from pulsed homogeneous infinite SHEM361-group thermal systems
    
## Benchmark verification (Code-to-code comparison)

Benchmark verification considers more involved problems that have no analytical solution.
Verification is guided through agreement in code-to-code comparison.

### Neutron transport

MC/DC results are compared to those of [OpenMC](https://github.com/openmc-dev/openmc)). Two physics modes are considered:
- Multigroup: Verification involves observing the $`N^{-0.5}`$ convergence in the relative differences of the two codes as the number of source particles $`N`$ is increased.
- Continuous energy: Verification involves observing the agreement in the results of the two codes.

#### [Multigroup](https://github.com/mcdc/mcdc-vv/tree/master/verification/benchmark/neutron/multigroup)
    
- Time-dependent version of the Kobayashi Dog-Leg transport benchmark [[Zenodo link](https://zenodo.org/records/15069882)]
- Four-phase C5G7 transient benchmark [[Zenodo link](https://zenodo.org/records/15719118)]

#### [Continuous energy](https://github.com/mcdc-project/mcdc-vv/tree/master/verification/benchmark/neutron/continuous_energy)

- Temporal spectrum evolutions of neutron-pulsed pincells with various materials:
  - UO2 and Water
  - UO2 and Helium

# Validation

# Performance
