# Literature and Web Sources for EBM Scan Strategies

## Academic Publications (PDF)

1. **Title:** Role of scan strategies on thermal gradient and solidification rate in electron beam powder bed fusion
   **Authors:** Y.S. Lee, M.M. Kirka, R.B. Dinwiddie, N. Raghavan, J. Turner, R.R. Dehoff, S.S. Babu
   **Journal:** Additive Manufacturing 22 (2018) 516-527
   **Link / DOI:** https://doi.org/10.1016/j.addma.2018.04.038
   **Relevance:** 
   - Proposes the **Ghost Beam** technique, exploring how beam splitting modulates the thermal history to reduce thermal gradients ($G$) and solidification rates ($R$).
   - Mentions that the ghost beam strategy uses sequential spot intervals (Primary and Secondary Spot).
   - Details **Spot-Consecutive** and **Spot-Ordered** multipass strategies.

## Web Sources

1. **Beam Splitting Strategy in EBM (Oak Ridge National Lab)**
   **Topic:** Overview of Ghost Beam strategy to "tune" the $G$ and $R$ variables to achieve desired grain morphologies (e.g. equiaxed grains).
   **Relevance:** Confirms that splitting the beam through rapid back-and-forth deflection of coordinates reduces $G$ and $\dot{T}$ to mitigate residual stress. The actual implementation in standard .B99 strictly relies on coordinate positioning to exploit this machine behavior mechanically.
