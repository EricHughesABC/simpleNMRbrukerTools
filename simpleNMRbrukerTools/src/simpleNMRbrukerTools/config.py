"""
bruker_nmr/src/config.py
"""

# Standard experiment configurations
EXPERIMENT_CONFIGS = {
    'HSQC': {
        'pulseprogram': [
            "hsqcedetgpsisp2.3.ptg", "hsqcedetgpsisp2.3", "gHSQCAD", 
            "hsqcedetgpsp.3", "gHSQC", "inv4gp.wu", "hsqcetgp",
            "gns_noah3-BSScc.eeh", "hsqcedetgpsisp2.4"
        ], 
        'nuclei': ['1H', '13C'], 
        'dimensions': 2
    },
    'HMBC': {
        'pulseprogram': [
            "ghmbc.wu", "gHMBC", "hmbcetgpl3nd", "hmbcetgpl3nd.ptg",
            "gHMBCAD", "hmbcgpndqf", "gns_noah3-BSScc.eeh", "shmbcctetgpl2nd",
            "hmbcedetgpl3nd"
        ],
        'nuclei': ['1H', '13C'], 
        'dimensions': 2
    },
    'COSY': {
        'pulseprogram': [
            "cosygpqf", "cosygp", "gcosy", "cosygpmfppqf", "cosygpmfqf", 
            "gCOSY", "cosygpppqf_ptype", "cosyqf45", "cosygpmfphpp",
            "cosygpppqf_ptype.jaa"
        ],    
        'nuclei': ['1H', '1H'], 
        'dimensions': 2
    },
    'NOESY': {
        'pulseprogram': ['noesygpphppzs'],
        'nuclei': ['1H', '1H'], 
        'dimensions': 2
    },
    'C13_1D': {
        'pulseprogram': ["zgdc30", "s2pul", "zgpg30", "zgzrse", "zg0dc.fr"],
        'nuclei': ['13C'], 
        'dimensions': 1
    },
    'H1_1D': {
        'pulseprogram': ["zg30", "s2pul", "zg", "zgcppr"],
        'nuclei': ['1H'], 
        'dimensions': 1
    },
    'PURESHIFT_1D': {
        'pulseprogram': ["ja_PSYCHE_pr_03b", "reset_psychetse.ptg"],
        'nuclei': ['1H'], 
        'dimensions': 2
    },
    'HSQC_CLIPCOSY': {
        'pulseprogram': ["hsqc_clip_cosy_mc_notation.eeh", "gns_noah3-BSScc.eeh"],
        'nuclei': ['1H', '13C'], 
        'dimensions': 2
    },
    'DDEPT_CH3_ONLY': {
        'pulseprogram': ['hcdeptedetgpzf'],
        'nuclei': ['1H', '13C'], 
        'dimensions': 2
    },
    'DEPT135': {
        'pulseprogram': ["dept135.wu", "DEPT", "deptsp135"],
        'nuclei': ['13C'],
        'dimensions': 1
    }
}