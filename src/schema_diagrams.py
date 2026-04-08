class SchemaDiagrams:
    """Sammlung von SVG_Schemata zur Darstellung der EBM Scanstrategien."""
    
    @staticmethod
    def get_raster() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow-raster" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563EB" />
    </marker>
  </defs>
  <style>
    .line { stroke: #2563EB; stroke-width: 3; fill: none; marker-end: url(#arrow-raster); }
    .jump { stroke: #9CA3AF; stroke-width: 2; stroke-dasharray: 4 4; fill: none; }
    .text { font-family: sans-serif; font-size: 12px; fill: #374151; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <!-- Linien -->
  <path class="line" d="M 100 40 L 500 40" />
  <path class="jump" d="M 500 40 L 500 80" />
  <path class="line" d="M 500 80 L 100 80" />
  <path class="jump" d="M 100 80 L 100 120" />
  <path class="line" d="M 100 120 L 500 120" />
  <path class="jump" d="M 500 120 L 500 160" />
  <path class="line" d="M 500 160 L 100 160" />
  
  <!-- Beschriftungen -->
  <path d="M 250 40 L 250 80" stroke="#DC2626" stroke-width="1.5" />
  <text x="260" y="65" class="text" fill="#DC2626">Hatch Spacing</text>
  <circle cx="350" cy="40" r="3" fill="#16A34A" />
  <circle cx="365" cy="40" r="3" fill="#16A34A" />
  <text x="340" y="25" class="text" fill="#16A34A">Punkt-Abstand</text>
</svg>"""

    @staticmethod
    def get_spot_consecutive() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow-spot" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563EB" />
    </marker>
  </defs>
  <style>
    .jump { stroke: #9CA3AF; stroke-width: 1.5; stroke-dasharray: 3 3; fill: none; }
    .spot { fill: #2563EB; }
    .text { font-family: sans-serif; font-size: 12px; fill: #374151; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <!-- Row 1 -->
  <g stroke="#2563EB" stroke-width="1.5" marker-end="url(#arrow-spot)">
    <line x1="100" y1="50" x2="135" y2="50" />
    <line x1="150" y1="50" x2="185" y2="50" />
    <line x1="200" y1="50" x2="235" y2="50" />
    <line x1="250" y1="50" x2="285" y2="50" />
  </g>
  <circle cx="100" cy="50" r="5" class="spot"/>
  <circle cx="150" cy="50" r="5" class="spot"/>
  <circle cx="200" cy="50" r="5" class="spot"/>
  <circle cx="250" cy="50" r="5" class="spot"/>
  <circle cx="300" cy="50" r="5" class="spot"/>
  
  <text x="95" y="35" class="text" font-weight="bold">1</text>
  <text x="145" y="35" class="text" font-weight="bold">2</text>
  <text x="195" y="35" class="text" font-weight="bold">3</text>
  
  <path class="jump" d="M 300 50 L 300 100" />
  
  <!-- Row 2 -->
  <g stroke="#2563EB" stroke-width="1.5" marker-end="url(#arrow-spot)">
    <line x1="300" y1="100" x2="265" y2="100" />
    <line x1="250" y1="100" x2="215" y2="100" />
  </g>
  <circle cx="300" cy="100" r="5" class="spot"/>
  <circle cx="250" cy="100" r="5" class="spot"/>
  <circle cx="200" cy="100" r="5" class="spot"/>
  
  <text x="400" y="80" class="text">Konsekutive Sprünge zwischen den Aufpunkten</text>
</svg>"""

    @staticmethod
    def get_spot_ordered() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <style>
    .spot1 { fill: #2563EB; }
    .spot2 { fill: #16A34A; }
    .spot3 { fill: #DC2626; }
    .text { font-family: sans-serif; font-size: 14px; font-weight: bold; fill: #ffffff; text-anchor: middle;}
    .desc { font-family: sans-serif; font-size: 12px; fill: #374151; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <!-- Spots -->
  <circle cx="100" cy="100" r="15" class="spot1"/><text x="100" y="105" class="text">1</text>
  <circle cx="150" cy="100" r="15" class="spot2"/><text x="150" y="105" class="text">2</text>
  <circle cx="200" cy="100" r="15" class="spot3"/><text x="200" y="105" class="text">3</text>
  <circle cx="250" cy="100" r="15" class="spot1"/><text x="250" y="105" class="text">4</text>
  <circle cx="300" cy="100" r="15" class="spot2"/><text x="300" y="105" class="text">5</text>
  <circle cx="350" cy="100" r="15" class="spot3"/><text x="350" y="105" class="text">6</text>
  <circle cx="400" cy="100" r="15" class="spot1"/><text x="400" y="105" class="text">7</text>
  <circle cx="450" cy="100" r="15" class="spot2"/><text x="450" y="105" class="text">8</text>
  <circle cx="500" cy="100" r="15" class="spot3"/><text x="500" y="105" class="text">9</text>
  
  <text x="100" y="150" class="desc" fill="#2563EB">Pass 1: 1→4→7</text>
  <text x="250" y="150" class="desc" fill="#16A34A">Pass 2: 2→5→8</text>
  <text x="400" y="150" class="desc" fill="#DC2626">Pass 3: 3→6→9</text>
</svg>"""

    @staticmethod
    def get_ghost_beam() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow-ghost" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#9CA3AF" />
    </marker>
  </defs>
  <style>
    .primary { fill: #2563EB; }
    .ghost { fill: #DC2626; stroke: #DC2626; stroke-width: 2; fill-opacity: 0.2; }
    .jump { stroke: #9CA3AF; stroke-width: 1.5; stroke-dasharray: 4 4; fill: none; marker-end: url(#arrow-ghost);}
    .text { font-family: sans-serif; font-size: 14px; fill: #374151; font-weight: bold;}
    .desc { font-family: sans-serif; font-size: 12px; fill: #374151; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <circle cx="450" cy="80" r="12" class="primary"/><text x="445" y="60" class="text" fill="#2563EB">P</text>
  <circle cx="250" cy="80" r="8"  class="ghost"/><text x="245" y="60" class="text" fill="#DC2626">S</text>
  
  <path class="jump" d="M 450 80 Q 350 40 250 80" />
  <path class="jump" d="M 250 80 Q 350 120 480 80" />
  
  <circle cx="480" cy="80" r="12" class="primary" fill-opacity="0.5"/>
  <circle cx="280" cy="80" r="8"  class="ghost" stroke-opacity="0.5"/>
  
  <path d="M 250 130 L 450 130" stroke="#374151" stroke-width="1.5" />
  <line x1="250" y1="125" x2="250" y2="135" stroke="#374151" stroke-width="1.5"/>
  <line x1="450" y1="125" x2="450" y2="135" stroke="#374151" stroke-width="1.5"/>
  <text x="310" y="150" class="desc">Skip Spacing (Lag)</text>
</svg>"""

    @staticmethod
    def get_island() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <style>
    .cell-1 { fill: #2563EB; fill-opacity: 0.2; stroke: #2563EB; stroke-width: 1; }
    .cell-2 { fill: #16A34A; fill-opacity: 0.2; stroke: #16A34A; stroke-width: 1; }
    .text { font-family: sans-serif; font-size: 14px; font-weight: bold; fill: #374151; text-anchor: middle;}
    .hatch { stroke: #2563EB; stroke-width: 1; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <g transform="translate(150, 20)">
    <!-- Row 1 -->
    <rect x="0" y="0" width="40" height="40" class="cell-1"/>
    <rect x="40" y="0" width="40" height="40" class="cell-2"/>
    <rect x="80" y="0" width="40" height="40" class="cell-1"/>
    <rect x="120" y="0" width="40" height="40" class="cell-2"/>
    <!-- Row 2 -->
    <rect x="0" y="40" width="40" height="40" class="cell-2"/>
    <rect x="40" y="40" width="40" height="40" class="cell-1"/>
    <rect x="80" y="40" width="40" height="40" class="cell-2"/>
    <rect x="120" y="40" width="40" height="40" class="cell-1"/>
    <!-- Row 3 -->
    <rect x="0" y="80" width="40" height="40" class="cell-1"/>
    <rect x="40" y="80" width="40" height="40" class="cell-2"/>
    <rect x="80" y="80" width="40" height="40" class="cell-1"/>
    <rect x="120" y="80" width="40" height="40" class="cell-2"/>
    
    <!-- Mini Hatch in first cell -->
    <line x1="5" y1="10" x2="35" y2="10" class="hatch"/>
    <line x1="5" y1="20" x2="35" y2="20" class="hatch"/>
    <line x1="5" y1="30" x2="35" y2="30" class="hatch"/>
  </g>
  
  <text x="450" y="80" class="text" fill="#2563EB">Phase 1 (Dunkel)</text>
  <text x="450" y="110" class="text" fill="#16A34A">Phase 2 (Hell)</text>
</svg>"""

    @staticmethod
    def get_hilbert() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow-hil" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563EB" />
    </marker>
  </defs>
  <style>
    .path { fill: none; stroke: #2563EB; stroke-width: 3; stroke-linejoin: round; }
    .text { font-family: sans-serif; font-size: 14px; fill: #374151; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <path class="path" d="M 220 160 L 220 120 L 260 120 L 260 160 L 300 160 L 300 120 L 340 120 L 340 160 L 380 160 L 380 120 L 380 80 L 340 80 L 340 40 L 380 40 L 300 40 L 300 80 L 260 80 L 260 40 L 220 40 L 220 80" marker-end="url(#arrow-hil)"/>
  
  <text x="420" y="100" class="text">Ordnung 2 (16 Segmente)</text>
</svg>"""

    @staticmethod
    def get_spiral() -> str:
        return """<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow-spi" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563EB" />
    </marker>
  </defs>
  <style>
    .path { fill: none; stroke: #2563EB; stroke-width: 2.5; stroke-linejoin: round; }
    .jump { stroke: #9CA3AF; stroke-width: 1.5; stroke-dasharray: 4 4; fill: none; marker-end: url(#arrow-spi);}
    .text { font-family: sans-serif; font-size: 14px; fill: #374151; }
  </style>
  <rect width="600" height="200" fill="#ffffff" />
  
  <rect x="200" y="30" width="200" height="140" class="path" />
  <rect x="220" y="50" width="160" height="100" class="path" />
  <rect x="240" y="70" width="120" height="60" class="path" />
  
  <path class="jump" d="M 300 30 L 300 50" />
  <path class="jump" d="M 300 50 L 300 70" />
  
  <text x="430" y="100" class="text">Inward Spiraling (Keine 180° Wenden)</text>
</svg>"""
