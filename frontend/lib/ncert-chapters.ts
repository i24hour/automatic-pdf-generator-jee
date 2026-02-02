/**
 * NCERT Chapters for Class 11 and 12
 * Used for searchable dropdown in Test Generator
 * Covers: Physics, Chemistry, Maths (JEE), Zoology, Botany (NEET)
 */

export interface ChapterData {
    name: string;
    topics?: string[]; // Optional sub-topics for more specific searches
}

export interface SubjectChapters {
    "Class 11": ChapterData[];
    "Class 12": ChapterData[];
}

export const ncertChapters: Record<string, SubjectChapters> = {
    Physics: {
        "Class 11": [
            { name: "Physical World", topics: ["Nature of physical laws", "Physics and technology"] },
            { name: "Units and Measurements", topics: ["SI units", "Dimensional analysis", "Significant figures", "Errors in measurement"] },
            { name: "Motion in a Straight Line", topics: ["Position", "Displacement", "Velocity", "Acceleration", "Kinematic equations", "Relative velocity"] },
            { name: "Motion in a Plane", topics: ["Vectors", "Projectile motion", "Uniform circular motion", "Angular velocity"] },
            { name: "Laws of Motion", topics: ["Newton's laws", "Friction", "Circular motion dynamics", "Impulse", "Momentum"] },
            { name: "Work, Energy and Power", topics: ["Work-energy theorem", "Kinetic energy", "Potential energy", "Conservation of energy", "Power", "Collisions"] },
            { name: "System of Particles and Rotational Motion", topics: ["Centre of mass", "Moment of inertia", "Torque", "Angular momentum", "Rolling motion"] },
            { name: "Gravitation", topics: ["Kepler's laws", "Newton's law of gravitation", "Gravitational potential", "Escape velocity", "Orbital velocity", "Satellites"] },
            { name: "Mechanical Properties of Solids", topics: ["Stress", "Strain", "Young's modulus", "Bulk modulus", "Shear modulus", "Poisson's ratio"] },
            { name: "Mechanical Properties of Fluids", topics: ["Pressure", "Pascal's law", "Bernoulli's principle", "Viscosity", "Surface tension", "Capillarity"] },
            { name: "Thermal Properties of Matter", topics: ["Temperature", "Heat transfer", "Thermal expansion", "Calorimetry", "Blackbody radiation"] },
            { name: "Thermodynamics", topics: ["Zeroth law", "First law", "Second law", "Heat engines", "Carnot cycle", "Entropy"] },
            { name: "Kinetic Theory", topics: ["Ideal gas equation", "Kinetic theory of gases", "Degrees of freedom", "Mean free path", "Specific heats"] },
            { name: "Oscillations", topics: ["Simple harmonic motion", "Damped oscillations", "Forced oscillations", "Resonance", "Pendulum"] },
            { name: "Waves", topics: ["Wave motion", "Sound waves", "Doppler effect", "Superposition", "Standing waves", "Beats"] },
        ],
        "Class 12": [
            { name: "Electric Charges and Fields", topics: ["Coulomb's law", "Electric field", "Electric dipole", "Gauss's law", "Electric flux"] },
            { name: "Electrostatic Potential and Capacitance", topics: ["Electric potential", "Equipotential surfaces", "Capacitors", "Dielectrics", "Energy stored"] },
            { name: "Current Electricity", topics: ["Ohm's law", "Kirchhoff's laws", "Wheatstone bridge", "Meter bridge", "Potentiometer", "EMF"] },
            { name: "Moving Charges and Magnetism", topics: ["Biot-Savart law", "Ampere's law", "Lorentz force", "Cyclotron", "Galvanometer"] },
            { name: "Magnetism and Matter", topics: ["Magnetic dipole", "Earth's magnetism", "Magnetic properties of materials", "Hysteresis"] },
            { name: "Electromagnetic Induction", topics: ["Faraday's law", "Lenz's law", "Eddy currents", "Self-inductance", "Mutual inductance"] },
            { name: "Alternating Current", topics: ["AC circuits", "LCR circuits", "Resonance", "Power factor", "Transformers"] },
            { name: "Electromagnetic Waves", topics: ["Displacement current", "EM spectrum", "Properties of EM waves"] },
            { name: "Ray Optics and Optical Instruments", topics: ["Reflection", "Refraction", "Lenses", "Prism", "Microscope", "Telescope", "Eye defects"] },
            { name: "Wave Optics", topics: ["Huygens principle", "Interference", "Diffraction", "Polarization", "Young's double slit"] },
            { name: "Dual Nature of Radiation and Matter", topics: ["Photoelectric effect", "Einstein's equation", "de Broglie wavelength", "Davisson-Germer experiment"] },
            { name: "Atoms", topics: ["Bohr model", "Hydrogen spectrum", "Rutherford model", "Atomic spectra"] },
            { name: "Nuclei", topics: ["Nuclear structure", "Mass defect", "Binding energy", "Radioactivity", "Nuclear fission", "Nuclear fusion"] },
            { name: "Semiconductor Electronics", topics: ["p-n junction", "Diode", "Zener diode", "Transistor", "Logic gates", "Rectifier"] },
        ],
    },

    Chemistry: {
        "Class 11": [
            { name: "Some Basic Concepts of Chemistry", topics: ["Laws of chemical combination", "Mole concept", "Atomic and molecular masses", "Stoichiometry"] },
            { name: "Structure of Atom", topics: ["Bohr model", "Quantum mechanical model", "Orbitals", "Electronic configuration", "Aufbau principle"] },
            { name: "Classification of Elements and Periodicity", topics: ["Periodic table", "Periodic trends", "Ionization energy", "Electron affinity", "Electronegativity"] },
            { name: "Chemical Bonding and Molecular Structure", topics: ["Ionic bond", "Covalent bond", "VSEPR theory", "Hybridization", "Molecular orbital theory"] },
            { name: "States of Matter", topics: ["Gas laws", "Ideal gas equation", "Kinetic theory", "Real gases", "Liquefaction"] },
            { name: "Thermodynamics", topics: ["First law", "Enthalpy", "Hess's law", "Entropy", "Gibbs energy", "Spontaneity"] },
            { name: "Equilibrium", topics: ["Chemical equilibrium", "Le Chatelier's principle", "Ionic equilibrium", "pH", "Buffer solutions", "Solubility product"] },
            { name: "Redox Reactions", topics: ["Oxidation number", "Balancing redox reactions", "Electrochemical cells"] },
            { name: "Hydrogen", topics: ["Position in periodic table", "Isotopes", "Preparation of hydrogen", "Hydrides", "Water"] },
            { name: "The s-Block Elements", topics: ["Alkali metals", "Alkaline earth metals", "Properties", "Compounds"] },
            { name: "The p-Block Elements", topics: ["Group 13 elements", "Group 14 elements", "Important compounds"] },
            { name: "Organic Chemistry - Basic Principles", topics: ["IUPAC nomenclature", "Isomerism", "Inductive effect", "Resonance", "Reaction mechanisms"] },
            { name: "Hydrocarbons", topics: ["Alkanes", "Alkenes", "Alkynes", "Aromatic hydrocarbons", "Benzene"] },
            { name: "Environmental Chemistry", topics: ["Air pollution", "Water pollution", "Greenhouse effect", "Ozone layer"] },
        ],
        "Class 12": [
            { name: "The Solid State", topics: ["Crystal lattice", "Unit cell", "Close packing", "Defects in solids", "Electrical properties"] },
            { name: "Solutions", topics: ["Concentration", "Colligative properties", "Raoult's law", "Osmotic pressure", "Van't Hoff factor"] },
            { name: "Electrochemistry", topics: ["Electrolytic cells", "Galvanic cells", "Nernst equation", "Conductance", "Kohlrausch's law", "Batteries", "Corrosion"] },
            { name: "Chemical Kinetics", topics: ["Rate of reaction", "Order of reaction", "Rate constant", "Arrhenius equation", "Collision theory"] },
            { name: "Surface Chemistry", topics: ["Adsorption", "Catalysis", "Colloids", "Emulsions", "Gels"] },
            { name: "General Principles of Isolation of Elements", topics: ["Metallurgy", "Concentration of ores", "Extraction", "Refining"] },
            { name: "The p-Block Elements", topics: ["Group 15", "Group 16", "Group 17", "Group 18", "Oxoacids", "Interhalogen compounds"] },
            { name: "The d and f Block Elements", topics: ["Transition metals", "Properties", "Lanthanoids", "Actinoids", "Interstitial compounds"] },
            { name: "Coordination Compounds", topics: ["Werner's theory", "IUPAC nomenclature", "Isomerism", "Bonding theories", "Crystal field theory"] },
            { name: "Haloalkanes and Haloarenes", topics: ["Nomenclature", "Preparation", "Reactions", "SN1 and SN2 mechanisms"] },
            { name: "Alcohols, Phenols and Ethers", topics: ["Preparation", "Properties", "Reactions", "Uses"] },
            { name: "Aldehydes, Ketones and Carboxylic Acids", topics: ["Preparation", "Aldol condensation", "Cannizzaro reaction", "Acidity"] },
            { name: "Amines", topics: ["Classification", "Preparation", "Properties", "Diazonium salts"] },
            { name: "Biomolecules", topics: ["Carbohydrates", "Proteins", "Enzymes", "Vitamins", "Nucleic acids"] },
            { name: "Polymers", topics: ["Classification", "Addition polymers", "Condensation polymers", "Biodegradable polymers"] },
            { name: "Chemistry in Everyday Life", topics: ["Drugs", "Chemicals in food", "Cleansing agents"] },
        ],
    },

    Maths: {
        "Class 11": [
            { name: "Sets", topics: ["Types of sets", "Venn diagrams", "Operations on sets", "De Morgan's laws"] },
            { name: "Relations and Functions", topics: ["Cartesian product", "Types of relations", "Types of functions", "Composition of functions"] },
            { name: "Trigonometric Functions", topics: ["Trigonometric ratios", "Trigonometric identities", "Graphs", "Inverse trigonometric functions"] },
            { name: "Principle of Mathematical Induction", topics: ["Principle of induction", "Applications"] },
            { name: "Complex Numbers and Quadratic Equations", topics: ["Complex numbers", "Argand plane", "Quadratic equations", "Roots and coefficients"] },
            { name: "Linear Inequalities", topics: ["Linear inequalities", "Graphical solution", "System of inequalities"] },
            { name: "Permutations and Combinations", topics: ["Fundamental counting principle", "Permutations", "Combinations", "Applications"] },
            { name: "Binomial Theorem", topics: ["Binomial expansion", "General term", "Middle term", "Applications"] },
            { name: "Sequences and Series", topics: ["Arithmetic progression", "Geometric progression", "Sum formulas", "Harmonic progression"] },
            { name: "Straight Lines", topics: ["Slope", "Equations of lines", "Distance formulas", "Angle between lines"] },
            { name: "Conic Sections", topics: ["Circle", "Parabola", "Ellipse", "Hyperbola"] },
            { name: "Introduction to Three Dimensional Geometry", topics: ["Coordinate axes", "Distance formula", "Section formula"] },
            { name: "Limits and Derivatives", topics: ["Limits", "Continuity", "Derivatives", "Algebra of derivatives"] },
            { name: "Mathematical Reasoning", topics: ["Statements", "Logical connectives", "Quantifiers", "Validity of statements"] },
            { name: "Statistics", topics: ["Mean", "Median", "Mode", "Variance", "Standard deviation"] },
            { name: "Probability", topics: ["Random experiments", "Sample space", "Events", "Probability axioms"] },
        ],
        "Class 12": [
            { name: "Relations and Functions", topics: ["Types of relations", "Equivalence relations", "Binary operations", "Inverse of a function"] },
            { name: "Inverse Trigonometric Functions", topics: ["Principal value", "Properties", "Graphs"] },
            { name: "Matrices", topics: ["Types of matrices", "Matrix operations", "Transpose", "Symmetric matrices"] },
            { name: "Determinants", topics: ["Properties", "Minors and cofactors", "Adjoint", "Inverse of matrix", "Cramer's rule"] },
            { name: "Continuity and Differentiability", topics: ["Continuity", "Differentiability", "Chain rule", "Implicit differentiation", "Logarithmic differentiation"] },
            { name: "Application of Derivatives", topics: ["Rate of change", "Tangents and normals", "Maxima and minima", "Mean value theorem"] },
            { name: "Integrals", topics: ["Indefinite integrals", "Integration techniques", "Definite integrals", "Properties of definite integrals"] },
            { name: "Application of Integrals", topics: ["Area under curves", "Area between curves"] },
            { name: "Differential Equations", topics: ["Order and degree", "Linear differential equations", "Homogeneous equations", "Variable separable"] },
            { name: "Vector Algebra", topics: ["Vectors", "Dot product", "Cross product", "Triple products"] },
            { name: "Three Dimensional Geometry", topics: ["Direction cosines", "Equation of line", "Equation of plane", "Angle between planes"] },
            { name: "Linear Programming", topics: ["Linear inequalities", "Graphical method", "Optimization problems"] },
            { name: "Probability", topics: ["Conditional probability", "Bayes' theorem", "Random variables", "Binomial distribution"] },
        ],
    },

    Zoology: {
        "Class 11": [
            { name: "The Living World", topics: ["Characteristics of life", "Taxonomy", "Nomenclature", "Classification hierarchy"] },
            { name: "Animal Kingdom", topics: ["Basis of classification", "Phylum Porifera", "Coelenterata", "Platyhelminthes", "Annelida", "Arthropoda", "Mollusca", "Echinodermata", "Chordata"] },
            { name: "Structural Organisation in Animals", topics: ["Animal tissues", "Epithelial tissue", "Connective tissue", "Muscular tissue", "Neural tissue", "Organ systems in cockroach"] },
            { name: "Biomolecules", topics: ["Carbohydrates", "Proteins", "Lipids", "Nucleic acids", "Enzymes"] },
            { name: "Digestion and Absorption", topics: ["Human digestive system", "Digestive enzymes", "Absorption", "Digestive disorders"] },
            { name: "Breathing and Exchange of Gases", topics: ["Respiratory organs", "Human respiratory system", "Mechanism of breathing", "Transport of gases", "Respiratory disorders"] },
            { name: "Body Fluids and Circulation", topics: ["Blood", "Lymph", "Human circulatory system", "Cardiac cycle", "ECG", "Circulatory disorders"] },
            { name: "Excretory Products and their Elimination", topics: ["Human excretory system", "Nephron", "Urine formation", "Osmoregulation", "Kidney disorders"] },
            { name: "Locomotion and Movement", topics: ["Types of movement", "Skeletal system", "Joints", "Muscular system", "Muscle contraction"] },
            { name: "Neural Control and Coordination", topics: ["Neuron", "Central nervous system", "Peripheral nervous system", "Reflex action", "Sense organs"] },
            { name: "Chemical Coordination and Integration", topics: ["Endocrine glands", "Hormones", "Mechanism of hormone action", "Hormonal disorders"] },
        ],
        "Class 12": [
            { name: "Human Reproduction", topics: ["Male reproductive system", "Female reproductive system", "Gametogenesis", "Menstrual cycle", "Fertilization", "Pregnancy", "Parturition"] },
            { name: "Reproductive Health", topics: ["Population control", "Contraception", "Infertility", "STDs", "Assisted reproductive technologies"] },
            { name: "Principles of Inheritance and Variation", topics: ["Mendelian genetics", "Chromosomal theory", "Linkage", "Sex determination", "Genetic disorders"] },
            { name: "Molecular Basis of Inheritance", topics: ["DNA structure", "DNA replication", "Transcription", "Translation", "Gene expression regulation", "Human genome project"] },
            { name: "Evolution", topics: ["Origin of life", "Evidences of evolution", "Darwin's theory", "Mechanisms of evolution", "Human evolution"] },
            { name: "Human Health and Disease", topics: ["Common diseases", "Immunity", "AIDS", "Cancer", "Drugs and alcohol abuse"] },
            { name: "Biotechnology: Principles and Processes", topics: ["Genetic engineering", "Recombinant DNA technology", "PCR", "Gene cloning"] },
            { name: "Biotechnology and its Applications", topics: ["Transgenic animals", "Gene therapy", "Bioethics"] },
            { name: "Organisms and Populations", topics: ["Organism and environment", "Populations", "Population ecology", "Population interactions"] },
        ],
    },

    Botany: {
        "Class 11": [
            { name: "The Living World", topics: ["Characteristics of life", "Taxonomy", "Taxonomical aids"] },
            { name: "Biological Classification", topics: ["Kingdom Monera", "Kingdom Protista", "Kingdom Fungi", "Kingdom Plantae", "Kingdom Animalia", "Viruses", "Viroids", "Lichens"] },
            { name: "Plant Kingdom", topics: ["Algae", "Bryophytes", "Pteridophytes", "Gymnosperms", "Angiosperms", "Plant life cycles"] },
            { name: "Morphology of Flowering Plants", topics: ["Root", "Stem", "Leaf", "Flower", "Fruit", "Seed", "Semi-technical description of plants"] },
            { name: "Anatomy of Flowering Plants", topics: ["Plant tissues", "Tissue system", "Anatomy of root", "Anatomy of stem", "Anatomy of leaf", "Secondary growth"] },
            { name: "Cell: The Unit of Life", topics: ["Cell theory", "Prokaryotic cell", "Eukaryotic cell", "Cell organelles"] },
            { name: "Cell Cycle and Cell Division", topics: ["Cell cycle", "Mitosis", "Meiosis", "Significance of cell division"] },
            { name: "Transport in Plants", topics: ["Diffusion", "Osmosis", "Plasmolysis", "Imbibition", "Transpiration", "Uptake of minerals", "Phloem transport"] },
            { name: "Mineral Nutrition", topics: ["Essential minerals", "Deficiency symptoms", "Nitrogen metabolism", "Nitrogen cycle", "Biological nitrogen fixation"] },
            { name: "Photosynthesis in Higher Plants", topics: ["Photosynthesis concept", "Photosynthetic pigments", "Light reaction", "Calvin cycle", "C4 pathway", "Photorespiration"] },
            { name: "Respiration in Plants", topics: ["Glycolysis", "Fermentation", "TCA cycle", "Electron transport chain", "Respiratory quotient"] },
        ],
        "Class 12": [
            { name: "Sexual Reproduction in Flowering Plants", topics: ["Flower structure", "Microsporogenesis", "Megasporogenesis", "Pollination", "Double fertilization", "Seed development", "Fruit development"] },
            { name: "Strategies for Enhancement in Food Production", topics: ["Plant breeding", "Tissue culture", "Single cell protein", "Biofortification"] },
            { name: "Microbes in Human Welfare", topics: ["Microbes in household products", "Industrial products", "Sewage treatment", "Biogas production", "Biocontrol agents", "Biofertilizers"] },
            { name: "Ecosystem", topics: ["Ecosystem structure", "Productivity", "Energy flow", "Ecological pyramids", "Nutrient cycling", "Ecological succession"] },
            { name: "Biodiversity and Conservation", topics: ["Biodiversity levels", "Biodiversity patterns", "Loss of biodiversity", "Biodiversity conservation"] },
        ],
    },
};

/**
 * Get all chapters for a subject as a flat list with class info
 */
export function getChaptersForSubject(subject: string): { class: string; name: string }[] {
    const subjectData = ncertChapters[subject];
    if (!subjectData) return [];

    const chapters: { class: string; name: string }[] = [];

    for (const [className, chapterList] of Object.entries(subjectData)) {
        for (const chapter of chapterList) {
            chapters.push({ class: className, name: chapter.name });
        }
    }

    return chapters;
}

/**
 * Get all topics (chapters + sub-topics) for searching
 */
export function getAllTopicsForSubject(subject: string): string[] {
    const subjectData = ncertChapters[subject];
    if (!subjectData) return [];

    const topics: string[] = [];

    for (const chapterList of Object.values(subjectData)) {
        for (const chapter of chapterList) {
            topics.push(chapter.name);
            if (chapter.topics) {
                topics.push(...chapter.topics);
            }
        }
    }

    return topics;
}

/**
 * Search chapters and topics matching a query
 */
export function searchChapters(
    subject: string,
    query: string
): { class: string; name: string; matchedTopic?: string }[] {
    const subjectData = ncertChapters[subject];
    if (!subjectData || !query.trim()) return getChaptersForSubject(subject);

    const normalizedQuery = query.toLowerCase().trim();
    const results: { class: string; name: string; matchedTopic?: string }[] = [];

    for (const [className, chapterList] of Object.entries(subjectData)) {
        for (const chapter of chapterList) {
            // Check if chapter name matches
            if (chapter.name.toLowerCase().includes(normalizedQuery)) {
                results.push({ class: className, name: chapter.name });
            }
            // Check if any topic matches
            else if (chapter.topics) {
                const matchedTopic = chapter.topics.find((t: string) =>
                    t.toLowerCase().includes(normalizedQuery)
                );
                if (matchedTopic) {
                    results.push({
                        class: className,
                        name: chapter.name,
                        matchedTopic,
                    });
                }
            }
        }
    }

    return results;
}

/**
 * Get chapters for multiple subjects
 */
export function getChaptersForMultipleSubjects(subjects: string[]): { class: string; name: string }[] {
    let allChapters: { class: string; name: string }[] = [];
    for (const subject of subjects) {
        allChapters = [...allChapters, ...getChaptersForSubject(subject)];
    }
    return allChapters;
}

/**
 * Search across multiple subjects
 */
export function searchMultipleSubjects(
    subjects: string[],
    query: string
): { class: string; name: string; matchedTopic?: string }[] {
    const activeSubjects = subjects.length > 0 ? subjects : ["Physics"]; // Fallback
    let allResults: { class: string; name: string; matchedTopic?: string }[] = [];

    for (const subject of activeSubjects) {
        const results = searchChapters(subject, query);
        // Add subject info to results if needed, but for now just merging
        // We might want to deduplicate but usually chapters are distinct per subject
        allResults = [...allResults, ...results];
    }

    return allResults;
}

/**
 * Detect subject from query locally
 */
export function detectSubjectFromQuery(query: string): string[] {
    const normalizedQuery = query.toLowerCase().trim();
    if (normalizedQuery.length < 3) return [];

    const detectedSubjects: string[] = [];

    // Check strict mappings first (optional, for common keywords)
    const keywords: Record<string, string[]> = {
        "Maths": ["math", "algebra", "geometry", "calculus", "integration", "derivative", "trigonometry"],
        "Physics": ["physics", "force", "motion", "energy", "gravity", "optics", "magnetism"],
        "Chemistry": ["chemistry", "reaction", "organic", "inorganic", "equilibrium", "acid", "base"],
        "Zoology": ["zoology", "animal", "human", "reproduction", "digestion", "neural"],
        "Botany": ["botany", "plant", "flower", "photosynthesis", "leaf", "stem"]
    };

    for (const [subj, words] of Object.entries(keywords)) {
        if (words.some(w => normalizedQuery.includes(w))) {
            detectedSubjects.push(subj);
        }
    }

    // Iterate through all chapters
    for (const [subject, subjectData] of Object.entries(ncertChapters)) {
        let found = false;
        // Check both classes
        for (const chapterList of Object.values(subjectData)) {
            for (const chapter of chapterList) {
                if (chapter.name.toLowerCase().includes(normalizedQuery)) {
                    detectedSubjects.push(subject);
                    found = true;
                    break;
                }
                if (chapter.topics) {
                    if (chapter.topics.some((t: string) => t.toLowerCase().includes(normalizedQuery))) {
                        detectedSubjects.push(subject);
                        found = true;
                        break;
                    }
                }
            }
            if (found) break;
        }
    }

    // Deduplicate
    return [...new Set(detectedSubjects)];
}
