/**
 * GATE Exam Chapter/Topic lists per paper
 * Used for the searchable topic dropdown when GATE is selected
 */

export interface GateChapter {
    name: string;
    topics?: string[];
}

export const gateChapters: Record<string, GateChapter[]> = {
    CSE: [
        // Engineering Mathematics
        { name: "Discrete Mathematics", topics: ["Propositional and first-order logic", "Sets, relations, functions", "Graphs", "Partial orders", "Lattices", "Combinatorics"] },
        { name: "Linear Algebra", topics: ["Matrices", "Determinants", "Eigenvalues and eigenvectors", "LU decomposition", "Systems of linear equations"] },
        { name: "Calculus", topics: ["Limits and continuity", "Differentiation", "Integration", "Maxima and minima", "Mean value theorem"] },
        { name: "Probability and Statistics", topics: ["Random variables", "Probability distributions", "Conditional probability", "Bayes' theorem", "Mean, variance, standard deviation", "Hypothesis testing"] },
        // Core CSE
        { name: "Programming and Data Structures", topics: ["C programming", "Arrays", "Linked lists", "Stacks", "Queues", "Trees", "Graphs", "Recursion"] },
        { name: "Algorithms", topics: ["Asymptotic complexity", "Sorting algorithms", "Searching algorithms", "Graph algorithms (BFS, DFS, Dijkstra, Kruskal, Prim)", "Dynamic programming", "Greedy algorithms", "Divide and conquer", "NP-completeness"] },
        { name: "Theory of Computation", topics: ["Regular languages and finite automata", "Context-free languages and CFG", "Pushdown automata", "Turing machines", "Decidability", "Complexity classes (P, NP, NP-complete)"] },
        { name: "Compiler Design", topics: ["Lexical analysis", "Syntax analysis", "Parsing (LL, LR)", "Semantic analysis", "Intermediate code generation", "Code optimization", "Runtime environments"] },
        { name: "Operating Systems", topics: ["Processes and threads", "CPU scheduling", "Process synchronization", "Deadlocks", "Memory management", "Virtual memory", "File systems", "I/O systems"] },
        { name: "Databases", topics: ["ER model", "Relational model", "SQL", "Normalization", "Transactions", "Concurrency control", "Indexing and B-trees", "Query processing"] },
        { name: "Computer Networks", topics: ["OSI and TCP/IP model", "Data link layer", "Network layer", "Transport layer", "Application layer", "Routing algorithms", "IP addressing and subnetting", "DNS, HTTP, SMTP"] },
        { name: "Computer Organization and Architecture", topics: ["Number systems", "Boolean algebra and logic gates", "Combinational circuits", "Sequential circuits", "CPU design", "Memory hierarchy", "Cache", "Pipeline", "I/O organization"] },
        { name: "Digital Logic", topics: ["Boolean algebra", "Logic gates", "Minimization (K-map)", "Combinational circuits (adders, multiplexers)", "Sequential circuits (flip-flops, counters, registers)"] },
    ],
    ECE: [
        { name: "Engineering Mathematics", topics: ["Linear algebra", "Calculus", "Differential equations", "Complex variables", "Probability and statistics", "Numerical methods"] },
        { name: "Networks, Signals and Systems", topics: ["Network theorems", "Graph theory", "Two-port networks", "Continuous-time signals", "Discrete-time signals", "Fourier series and transform", "Laplace transform", "Z-transform", "Sampling theorem"] },
        { name: "Electronic Devices", topics: ["Energy bands", "Diodes", "BJT", "MOSFET", "Small signal models", "Biasing", "Photonic devices"] },
        { name: "Analog Circuits", topics: ["Diode circuits", "BJT and MOSFET amplifiers", "Operational amplifiers", "Feedback amplifiers", "Oscillators", "Filters"] },
        { name: "Digital Circuits", topics: ["Boolean algebra", "Logic gates", "Combinational circuits", "Sequential circuits", "Flip-flops", "Counters", "A/D and D/A converters", "Semiconductor memories"] },
        { name: "Control Systems", topics: ["Transfer function", "Block diagrams", "Signal flow graphs", "Time domain analysis", "Frequency domain analysis", "Bode plot", "Nyquist criterion", "Stability", "PID controllers"] },
        { name: "Communications", topics: ["Amplitude modulation", "Frequency modulation", "Phase modulation", "Digital modulation (ASK, FSK, PSK, QAM)", "SNR", "Bandwidth", "Random processes in communications"] },
        { name: "Electromagnetics", topics: ["Maxwell's equations", "Plane waves", "Transmission lines", "Waveguides", "Antennas", "Boundary conditions"] },
    ],
    ME: [
        { name: "Engineering Mathematics", topics: ["Linear algebra", "Calculus", "Differential equations", "Complex variables", "Probability and statistics", "Numerical methods"] },
        { name: "Applied Mechanics and Design", topics: ["Engineering mechanics (statics, dynamics)", "Strength of materials", "Theory of machines", "Vibrations", "Machine design"] },
        { name: "Fluid Mechanics and Thermal Sciences", topics: ["Fluid statics", "Fluid kinematics", "Fluid dynamics", "Bernoulli equation", "Viscous flow", "Heat transfer (conduction, convection, radiation)", "Thermodynamics (laws, cycles)", "Power engineering", "Refrigeration"] },
        { name: "Manufacturing and Industrial Engineering", topics: ["Engineering materials", "Casting", "Forming", "Joining (welding, brazing)", "Machining", "Metrology", "Computer integrated manufacturing", "Production planning and control", "Operations research"] },
    ],
    DA: [
        { name: "Statistics", topics: ["Descriptive statistics", "Probability", "Distributions", "Hypothesis testing", "Regression", "Bayes' theorem"] },
        { name: "Linear Algebra", topics: ["Matrices", "Eigenvalues and eigenvectors", "SVD", "PCA"] },
        { name: "Calculus and Optimization", topics: ["Partial derivatives", "Gradient descent", "Convex optimization", "Lagrange multipliers"] },
        { name: "Programming and Algorithms", topics: ["Python programming", "Data structures", "Sorting and searching", "Complexity analysis"] },
        { name: "Database Management", topics: ["SQL", "Relational model", "ER model", "Normalization", "Query processing"] },
        { name: "Machine Learning", topics: ["Supervised learning", "Unsupervised learning", "Linear regression", "Logistic regression", "Decision trees", "SVM", "Clustering (K-means)", "Neural networks", "Overfitting and regularization", "Cross-validation"] },
        { name: "Artificial Intelligence", topics: ["Search algorithms", "Knowledge representation", "Planning", "Natural language processing basics"] },
        { name: "Data Visualization", topics: ["Matplotlib", "Seaborn", "Tableau basics", "Charts and graphs", "Dashboard design"] },
    ],
    EE: [
        { name: "Engineering Mathematics", topics: ["Linear algebra", "Calculus", "Complex analysis", "Differential equations", "Probability and statistics"] },
        { name: "Electric Circuits", topics: ["KVL and KCL", "Network theorems", "AC circuits", "Resonance", "Two-port networks", "Laplace transform"] },
        { name: "Electromagnetic Fields", topics: ["Coulomb's law", "Gauss's law", "Biot-Savart law", "Faraday's law", "Maxwell's equations", "Boundary conditions"] },
        { name: "Signals and Systems", topics: ["Continuous-time signals", "Discrete-time signals", "Fourier series", "Laplace transform", "Z-transform", "Filtering"] },
        { name: "Electrical Machines", topics: ["DC machines", "Transformers", "Induction machines", "Synchronous machines", "Drives"] },
        { name: "Power Systems", topics: ["Power generation", "Transmission lines", "Load flow analysis", "Fault analysis", "Protection systems", "HVDC"] },
        { name: "Control Systems", topics: ["Transfer function", "Block diagrams", "Time response", "Frequency response", "Bode plot", "Nyquist criterion", "Stability", "PID", "State space"] },
        { name: "Power Electronics", topics: ["Power semiconductor devices", "Diode rectifiers", "AC to DC converters", "DC to DC converters", "Inverters", "PWM"] },
        { name: "Analog Electronics", topics: ["Diodes", "BJT and MOSFET", "Amplifiers", "Op-amps", "Oscillators", "Feedback"] },
        { name: "Digital Electronics", topics: ["Boolean algebra", "Logic gates", "Combinational circuits", "Sequential circuits", "A/D and D/A converters"] },
    ],
    CE: [
        { name: "Engineering Mathematics", topics: ["Linear algebra", "Calculus", "Differential equations", "Probability and statistics", "Numerical methods"] },
        { name: "Structural Engineering", topics: ["Engineering mechanics", "Solid mechanics", "Structural analysis", "Steel structures", "Concrete structures", "Pre-stressed concrete"] },
        { name: "Geotechnical Engineering", topics: ["Soil mechanics", "Foundation engineering", "Earth pressure", "Slope stability"] },
        { name: "Water Resources Engineering", topics: ["Fluid mechanics", "Hydraulics", "Hydrology", "Irrigation"] },
        { name: "Environmental Engineering", topics: ["Water supply engineering", "Wastewater engineering", "Air pollution", "Solid waste management", "Environmental impact"] },
        { name: "Transportation Engineering", topics: ["Highway engineering", "Traffic engineering", "Railway engineering", "Airport engineering"] },
        { name: "Geomatics Engineering", topics: ["Surveying", "Remote sensing", "GIS"] },
    ],
    IN: [
        { name: "Engineering Mathematics", topics: ["Linear algebra", "Calculus", "Complex variables", "Probability and statistics", "Numerical methods"] },
        { name: "Instrumentation Engineering", topics: ["Measurement fundamentals", "Transducers", "Signal conditioning", "Data acquisition"] },
        { name: "Control Systems", topics: ["Transfer function", "Time response", "Frequency response", "Stability", "PID controllers", "State space"] },
        { name: "Sensors and Industrial Instrumentation", topics: ["Temperature sensors", "Pressure sensors", "Flow meters", "Level sensors", "Analytical instruments"] },
        { name: "Analog Electronics", topics: ["Op-amps", "Amplifiers", "Filters", "Oscillators"] },
        { name: "Digital Electronics", topics: ["Logic gates", "Combinational and sequential circuits", "ADC and DAC", "Microprocessors"] },
        { name: "Signals and Systems", topics: ["Fourier transform", "Laplace transform", "Z-transform", "Sampling theorem"] },
        { name: "Communication and Optical Instrumentation", topics: ["Modulation techniques", "Optical fibers", "Optical sensors", "Laser basics"] },
    ],
};

/**
 * Get chapters for a GATE paper as a flat list
 */
export function getGateChapters(paper: string): { name: string }[] {
    const chapters = gateChapters[paper];
    if (!chapters) return [];
    return chapters.map(ch => ({ name: ch.name }));
}

/**
 * Search GATE chapters by query
 */
export function searchGateChapters(paper: string, query: string): { name: string; matchedTopic?: string }[] {
    const chapters = gateChapters[paper];
    if (!chapters) return [];
    if (!query.trim()) return chapters.map(ch => ({ name: ch.name }));

    const q = query.toLowerCase().trim();
    const results: { name: string; matchedTopic?: string }[] = [];

    for (const chapter of chapters) {
        if (chapter.name.toLowerCase().includes(q)) {
            results.push({ name: chapter.name });
        } else if (chapter.topics) {
            const matched = chapter.topics.find(t => t.toLowerCase().includes(q));
            if (matched) results.push({ name: chapter.name, matchedTopic: matched });
        }
    }

    return results;
}
