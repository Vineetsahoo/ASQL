# ASQL Cinematic Web3 Design System

## 1. Core Philosophy & Vision
The ASQL Cinematic Web3 design language is engineered for high-performance developer tools that demand an ultra-premium, "Awwwards-winning" aesthetic. 

**Core Tenets:**
- **Dark Void Aesthetic:** Eliminate traditional white space. Instead, use "dark space" (pitch black) to create infinite depth, allowing data and UI panels to float.
- **Glassmorphism & Depth:** Information should sit on frosted glass panels (`backdrop-filter`) that gently blur the complex WebGL environments behind them.
- **Vivid Restraint:** Use our signature neon red strictly for interactions, focal points, and critical data anomalies.
- **Physical Interactivity:** The UI must feel alive. Elements should respond to mouse velocity, and scroll mechanics must be overridden with momentum-based smooth scrolling.

---

## 2. CSS Variable Architecture (Tokens)

Embed this token map in your `:root` or global CSS file. Do not hardcode colors in your stylesheets.

```css
:root {
    /* Core Backgrounds */
    --bg-dark: #030303;               /* The infinite void background */
    --surface: rgba(15, 15, 15, 0.6); /* Default glass panel */
    --surface-hover: rgba(25, 25, 25, 0.8); /* Hovered glass panel */
    
    /* Signature Accents */
    --primary: #FF0000;               /* Vivid Neon Red */
    --primary-glow: rgba(255, 0, 0, 0.4); /* Volumetric glow */
    
    /* Typography */
    --text-main: #FFFFFF;             /* Primary headings and paragraphs */
    --text-muted: #888888;            /* Secondary text, metadata, nav links */
    
    /* Borders & Outlines */
    --border: rgba(255, 255, 255, 0.08); /* Subtle container outlines */
    --border-highlight: rgba(255, 0, 0, 0.5); /* Active/Hover container outlines */
    
    /* Semantic Severity Map (For Reports & Dashboards) */
    --ap-high: #FF0000;               /* Critical anomaly / Full Table Scan */
    --ap-med: #FF5500;                /* Warning / Suboptimal Query */
    --ap-low: #00E676;                /* Good / Optimized */
}
```

---

## 3. Typography System

We utilize two premium Google Fonts. **Space Grotesk** drives the overarching layout architecture, while **Roboto Mono** manages data and code.

### Font Definitions
- **Primary:** `font-family: 'Space Grotesk', sans-serif;` (Weights: 300, 400, 500, 600, 700)
- **Secondary:** `font-family: 'Roboto Mono', monospace;` (Weights: 400, 500)

### Typographic Scales & Styles

**1. Hero Headings (`<h1>`)**
Uses `clamp()` for fluid responsiveness across all viewports.
```css
h1 {
    font-size: clamp(2.5rem, 4vw, 4rem);
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1.1;
}
/* For cinematic outlined text variations */
h1 .outline {
    color: transparent;
    -webkit-text-stroke: 1px rgba(255,255,255,0.3);
}
```

**2. Standard Body Text (`<p>`)**
```css
p {
    font-size: 1rem;
    color: var(--text-muted);
    line-height: 1.6;
}
```

**3. Code Blocks & Snippets (`<pre>`)**
```css
pre {
    background: #000;
    padding: 1.2rem;
    border-radius: 12px;
    font-family: 'Roboto Mono', monospace;
    font-size: 0.85rem;
    color: #E0E0E0;
    border: 1px solid var(--border);
    border-left: 3px solid var(--primary); /* Signature red stripe */
}
```

---

## 4. Component Blueprints

### A. The Glassmorphic Container
The foundational building block for all layout elements (Sidebars, Navbars, Data Tables, Feature Cards).

**CSS:**
```css
.glass-card {
    background: var(--surface);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px); /* Safari support */
    border: 1px solid var(--border);
    border-radius: 24px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.glass-card:hover {
    transform: translateY(-4px) scale(1.01);
    background: var(--surface-hover);
    border-color: var(--border-highlight);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}
```

### B. Magnetic Web3 Button
A premium interaction that detaches the button from its origin and pulls it toward the user's cursor on hover.

**HTML:**
```html
<a href="#" class="btn-web3" id="magneticBtn">
    <span>Launch Platform</span>
</a>
```

**CSS:**
```css
.btn-web3 {
    display: inline-flex;
    align-items: center;
    padding: 0 40px;
    height: 64px;
    border-radius: 100px;
    background: rgba(255,0,0,0.1);
    border: 1px solid var(--primary);
    color: #FFF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    box-shadow: 0 0 20px rgba(255,0,0,0.2);
    overflow: hidden;
    position: relative;
    transition: color 0.3s ease, box-shadow 0.3s ease;
}
```

**GSAP Logic (JS):**
```javascript
const btn = document.getElementById('magneticBtn');
btn.addEventListener('mousemove', (e) => {
    const rect = btn.getBoundingClientRect();
    const x = (e.clientX - rect.left) - rect.width / 2;
    const y = (e.clientY - rect.top) - rect.height / 2;
    
    gsap.to(btn, { x: x * 0.4, y: y * 0.4, duration: 0.6, ease: "power3.out" });
});
btn.addEventListener('mouseleave', () => {
    gsap.to(btn, { x: 0, y: 0, duration: 0.8, ease: "elastic.out(1, 0.3)" });
});
```

---

## 5. Animation & Scroll Pipeline

This design system **mandates** hijacking the browser's default scroll behavior to achieve a "cinematic" pacing.

### Lenis Smooth Scrolling
Must be initialized before any GSAP animations.
```javascript
const lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smooth: true
});
function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
}
requestAnimationFrame(raf);
```

### GSAP Reveal Standard (Clip-Path Masks)
Use this for massive headers. It slices the text upward from an invisible boundary.
```javascript
gsap.from(".reveal-text", { 
    y: 100, 
    opacity: 0, 
    clipPath: "polygon(0 0, 100% 0, 100% 0%, 0% 0%)",
    duration: 1.2,
    ease: "power4.out"
});
```

---

## 6. WebGL Background Architectures (Three.js)

Do not use static images for backgrounds. The background must be a living, 3D `canvas` fixed behind the DOM.

**Canvas Setup:**
```css
#webgl-canvas {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    z-index: -1;
    pointer-events: none;
}
```

**Supported Scenes:**
1. **The Artifact (Used in `docs.html`)**: A massive `THREE.TorusKnotGeometry` wrapped in a wireframe `THREE.IcosahedronGeometry`. Physically spins in relation to the `Lenis` scroll position via `ScrollTrigger`.
2. **The Digital Sea & Floating Shards (Used in `report.html`)**: A fully 3D environment featuring an undulating wireframe terrain (`THREE.PlaneGeometry`) that emits a volumetric red glow, simulating an Aurora beam. Suspended above it are 40 floating, dark frosted-glass monoliths (`THREE.IcosahedronGeometry` with `MeshPhysicalMaterial`). 
   - **Scroll Interaction**: Utilizes `GSAP ScrollTrigger` with `scrub: 1.5` to physically fly the `PerspectiveCamera` over the rolling digital sea and through the floating data shards as the user scrolls down the page.

### Example WebGL Implementation (The Digital Sea)
```javascript
const initWebGL = () => {
    gsap.registerPlugin(ScrollTrigger);
    
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030303, 0.02);
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 5, 25);

    // 1. Digital Aurora Sea
    const planeGeo = new THREE.PlaneGeometry(150, 150, 64, 64);
    const planeMat = new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true, transparent: true, opacity: 0.15 });
    const plane = new THREE.Mesh(planeGeo, planeMat);
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -10;
    scene.add(plane);

    // 2. Floating Data Shards
    // (Implementation relies on MeshPhysicalMaterial with transmission and thickness for glass refraction)
    
    // GSAP Scroll Fly-through
    gsap.to(camera.position, {
        z: -30, y: 2, ease: "power1.inOut",
        scrollTrigger: { trigger: "body", start: "top top", end: "bottom bottom", scrub: 1.5 }
    });
};
```

---

## 7. Data Visualization (Chart.js Integration)

When using Chart.js inside this design system, default browser tooltips and white backgrounds must be disabled.

**Global Web3 Theme Overrides:**
```javascript
Chart.defaults.color = '#888888';
Chart.defaults.font.family = "'Space Grotesk', sans-serif";
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 15, 15, 0.9)';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 0, 0, 0.5)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.titleColor = '#FFFFFF';
Chart.defaults.plugins.tooltip.bodyColor = '#FFFFFF';
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
```
