STRONG_SUBJECT_CHAPTER: dict[str, str] = {
    "PHYSICS": "Electrostatics",
    "CHEMISTRY": "Organic Chemistry (GOC)",
    "MATH": "Applications of Derivatives",
}

WEAK_SUBJECT_CHAPTER: dict[str, str] = {
    "PHYSICS": "Modern Physics",
    "CHEMISTRY": "Coordination Compounds",
    "MATH": "Complex Numbers",
}

JEE_CHAPTERS: dict[str, list[str]] = {
    "PHYSICS": [
        "Kinematics",
        "Laws of Motion",
        "Work, Energy and Power",
        "Rotational Motion",
        "Gravitation",
        "Properties of Matter",
        "Thermodynamics",
        "Kinetic Theory of Gases",
        "Oscillations",
        "Waves",
        "Electrostatics",
        "Current Electricity",
        "Magnetic Effects of Current",
        "Electromagnetic Induction",
        "Alternating Current",
        "Electromagnetic Waves",
        "Ray Optics",
        "Wave Optics",
        "Modern Physics",
        "Semiconductor Devices",
    ],
    "CHEMISTRY": [
        "Mole Concept",
        "Atomic Structure",
        "Chemical Bonding",
        "States of Matter",
        "Thermodynamics",
        "Equilibrium",
        "Redox Reactions",
        "Electrochemistry",
        "Chemical Kinetics",
        "Surface Chemistry",
        "Periodic Table",
        "General Organic Chemistry (GOC)",
        "Organic Chemistry (GOC)",
        "Hydrocarbons",
        "Haloalkanes and Haloarenes",
        "Alcohols, Phenols, Ethers",
        "Aldehydes and Ketones",
        "Carboxylic Acids",
        "Amines",
        "Coordination Compounds",
        "p-Block Elements",
        "d and f Block Elements",
        "Biomolecules",
        "Polymers",
    ],
    "MATH": [
        "Sets and Relations",
        "Complex Numbers",
        "Quadratic Equations",
        "Sequences and Series",
        "Permutations and Combinations",
        "Binomial Theorem",
        "Straight Lines",
        "Circles",
        "Conic Sections",
        "Limits and Continuity",
        "Differentiation",
        "Applications of Derivatives",
        "Indefinite Integration",
        "Definite Integration",
        "Differential Equations",
        "Vectors",
        "3D Geometry",
        "Matrices and Determinants",
        "Probability",
        "Statistics",
        "Trigonometry",
        "Inverse Trigonometry",
    ],
}


def get_suggested_strong_chapter(strong_subjects: list[str]) -> dict | None:
    if not strong_subjects:
        return None
    subject = strong_subjects[0]
    chapter = STRONG_SUBJECT_CHAPTER.get(subject) or JEE_CHAPTERS.get(subject, [""])[0]
    return {"subject": subject, "chapter": chapter}


def get_suggested_weak_chapter(weak_subjects: list[str]) -> dict | None:
    if not weak_subjects:
        return None
    subject = weak_subjects[0]
    chapter = WEAK_SUBJECT_CHAPTER.get(subject) or JEE_CHAPTERS.get(subject, [""])[0]
    return {"subject": subject, "chapter": chapter}
