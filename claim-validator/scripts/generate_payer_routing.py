#!/usr/bin/env python3
"""Generate payer_routing.json.gz with ~2,200 realistic US healthcare payer entries."""

import gzip
import json
import os
import random

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "claim_validator",
    "shared",
    "data",
    "payer_routing.json.gz",
)

# ── Clearinghouse definitions with their supported transaction types ──────────

CLEARINGHOUSES = {
    "change": {
        "supports": ["837P", "837I", "270/271", "276/277"],
    },
    "stedi": {
        "supports": ["837P", "270/271"],
    },
    "claimmd": {
        "supports": ["837P", "270/271"],
    },
    "waystar": {
        "supports": ["837P", "270/271", "278"],
    },
    "availity": {
        "supports": ["837P", "270/271", "276/277"],
    },
}

CH_NAMES = list(CLEARINGHOUSES.keys())

# ── Real payer IDs ────────────────────────────────────────────────────────────

MEDICARE_PAYERS = {
    "00882": "Medicare Part A",
    "00883": "Medicare Part B",
    "00884": "Medicare DME MAC",
    "00885": "Medicare HH+Hospice MAC",
    "00880": "Medicare Railroad",
    "14411": "Medicare MAC - Novitas (JH)",
    "14412": "Medicare MAC - Novitas (JL)",
    "12301": "Medicare MAC - NGS (JK)",
    "12302": "Medicare MAC - NGS (J6)",
    "13101": "Medicare MAC - Palmetto (JJ)",
    "13102": "Medicare MAC - Palmetto (JM)",
    "15101": "Medicare MAC - WPS (J5)",
    "15102": "Medicare MAC - WPS (J8)",
    "16003": "Medicare MAC - CGS (J15)",
    "17003": "Medicare MAC - First Coast (JN)",
    "12001": "Medicare MAC - National Government Services (JK)",
    "12002": "Medicare MAC - National Government Services (J6)",
    "11001": "Medicare Advantage - National",
    "11002": "Medicare Part D Plans",
    "00886": "Medicare ESRD",
    "00887": "Medicare Psychiatric",
    "00881": "Medicare - CWF",
}

# Medicaid – one per state + DC
MEDICAID_PAYERS = {
    "ALMED": "Alabama Medicaid",
    "AKMED": "Alaska Medicaid",
    "AZMED": "Arizona Medicaid (AHCCCS)",
    "ARMED": "Arkansas Medicaid",
    "CAMED": "California Medicaid (Medi-Cal)",
    "COMED": "Colorado Medicaid",
    "CTMED": "Connecticut Medicaid",
    "DEMED": "Delaware Medicaid",
    "DCMED": "District of Columbia Medicaid",
    "FLMED": "Florida Medicaid",
    "GAMED": "Georgia Medicaid",
    "HIMED": "Hawaii Medicaid (Quest)",
    "IDMED": "Idaho Medicaid",
    "ILMED": "Illinois Medicaid",
    "INMED": "Indiana Medicaid",
    "IAMED": "Iowa Medicaid",
    "KSMED": "Kansas Medicaid (KanCare)",
    "KYMED": "Kentucky Medicaid",
    "LAMED": "Louisiana Medicaid",
    "MEMED": "Maine Medicaid",
    "MDMED": "Maryland Medicaid",
    "MAMED": "Massachusetts Medicaid (MassHealth)",
    "MIMED": "Michigan Medicaid",
    "MNMED": "Minnesota Medicaid",
    "MSMED": "Mississippi Medicaid",
    "MOMED": "Missouri Medicaid (MO HealthNet)",
    "MTMED": "Montana Medicaid",
    "NEMED": "Nebraska Medicaid",
    "NVMED": "Nevada Medicaid",
    "NHMED": "New Hampshire Medicaid",
    "NJMED": "New Jersey Medicaid",
    "NMMED": "New Mexico Medicaid",
    "NYMED": "New York Medicaid",
    "NCMED": "North Carolina Medicaid",
    "NDMED": "North Dakota Medicaid",
    "OHMED": "Ohio Medicaid",
    "OKMED": "Oklahoma Medicaid",
    "ORMED": "Oregon Medicaid (OHP)",
    "PAMED": "Pennsylvania Medicaid",
    "RIMED": "Rhode Island Medicaid",
    "SCMED": "South Carolina Medicaid",
    "SDMED": "South Dakota Medicaid",
    "TNMED": "Tennessee Medicaid (TennCare)",
    "TXMED": "Texas Medicaid",
    "UTMED": "Utah Medicaid",
    "VTMED": "Vermont Medicaid",
    "VAMED": "Virginia Medicaid",
    "WAMED": "Washington Medicaid (Apple Health)",
    "WVMED": "West Virginia Medicaid",
    "WIMED": "Wisconsin Medicaid (ForwardHealth)",
    "WYMED": "Wyoming Medicaid",
}

MAJOR_COMMERCIAL = {
    "60054": "Aetna",
    "60054A": "Aetna Better Health",
    "60054B": "Aetna Medicare Advantage",
    "87726": "UnitedHealthcare",
    "87726A": "UHC Community Plan",
    "87726B": "UHC Medicare Advantage",
    "87726C": "UHC Student Resources",
    "87726D": "UHC West",
    "62308": "Cigna",
    "62308A": "Cigna Behavioral Health",
    "62308B": "Cigna Medicare Advantage",
    "61101": "Humana",
    "61101A": "Humana Medicare Advantage",
    "61101B": "Humana Military (Tricare East)",
    "25169": "Anthem",
    "25169A": "Anthem Blue Cross Blue Shield",
    "47198": "Centene",
    "47198A": "Centene - Ambetter",
    "47198B": "Centene - WellCare",
    "36273": "Molina Healthcare",
    "36273A": "Molina Medicare",
    "52629": "Kaiser Permanente",
    "52629A": "Kaiser Permanente - Northern CA",
    "52629B": "Kaiser Permanente - Southern CA",
    "52629C": "Kaiser Permanente - Northwest",
    "52629D": "Kaiser Permanente - Colorado",
    "52629E": "Kaiser Permanente - Georgia",
    "52629F": "Kaiser Permanente - Mid-Atlantic",
    "52629G": "Kaiser Permanente - Hawaii",
    "39026": "CVS/Aetna - Caremark",
    "91136": "Bright Health",
    "13551": "Elevance Health",
    "55204": "Guidewell / Florida Blue",
}

BCBS_AFFILIATES = {
    "00590": "BCBS Alabama",
    "84105": "BCBS Alaska (Premera)",
    "46045": "BCBS Arizona",
    "71063": "BCBS Arkansas",
    "91051": "BCBS California (Anthem)",
    "84101": "BCBS Colorado",
    "00803": "BCBS Connecticut",
    "00602": "BCBS Delaware",
    "00890": "BCBS DC (CareFirst)",
    "59140": "BCBS Florida (Florida Blue)",
    "00591": "BCBS Georgia",
    "99039": "BCBS Hawaii (HMSA)",
    "84103": "BCBS Idaho (Regence)",
    "00621": "BCBS Illinois",
    "25133": "BCBS Indiana (Anthem)",
    "00636": "BCBS Iowa (Wellmark)",
    "00639": "BCBS Kansas",
    "63843": "BCBS Kentucky (Anthem)",
    "00655": "BCBS Louisiana",
    "00658": "BCBS Maine (Anthem)",
    "00661": "BCBS Maryland (CareFirst)",
    "00680": "BCBS Massachusetts",
    "00683": "BCBS Michigan",
    "00690": "BCBS Minnesota",
    "00693": "BCBS Mississippi",
    "00695": "BCBS Missouri (Anthem)",
    "00700": "BCBS Montana",
    "47171": "BCBS Nebraska",
    "84104": "BCBS Nevada (Anthem)",
    "00716": "BCBS New Hampshire (Anthem)",
    "22099": "BCBS New Jersey (Horizon)",
    "00724": "BCBS New Mexico",
    "00803A": "BCBS New York (Excellus)",
    "80314": "BCBS New York (Empire)",
    "55204A": "BCBS North Carolina",
    "00731": "BCBS North Dakota",
    "00740": "BCBS Ohio (Anthem)",
    "00743": "BCBS Oklahoma",
    "84102": "BCBS Oregon (Regence)",
    "00750": "BCBS Pennsylvania (Highmark)",
    "00753": "BCBS Pennsylvania (Independence)",
    "00770": "BCBS Rhode Island",
    "00773": "BCBS South Carolina",
    "00780": "BCBS South Dakota (Wellmark)",
    "54771": "BCBS Tennessee",
    "84980": "BCBS Texas",
    "87848": "BCBS Utah (Regence)",
    "00810": "BCBS Vermont",
    "00813": "BCBS Virginia (Anthem)",
    "91062": "BCBS Washington (Premera)",
    "91062A": "BCBS Washington (Regence)",
    "00823": "BCBS West Virginia (Highmark)",
    "00826": "BCBS Wisconsin (Anthem)",
    "00829": "BCBS Wyoming",
}

GOVERNMENT_MILITARY = {
    "99726": "Tricare West",
    "99727": "Tricare East",
    "99728": "Tricare Overseas",
    "84146": "Tricare for Life",
    "12115": "Veterans Affairs (VA)",
    "12116": "VA Community Care",
    "75241": "CHAMPVA",
    "37064": "Indian Health Service",
    "52183": "Federal Employee Program (FEP)",
    "00810A": "FEHB - GEHA",
    "00810B": "FEHB - NALC",
    "00810C": "FEHB - Mail Handlers",
    "75242": "Peace Corps",
    "37065": "Bureau of Prisons Health",
}

REGIONAL_PLANS = {
    "39144": "Harvard Pilgrim Health Care",
    "04212": "Tufts Health Plan",
    "06105": "ConnectiCare",
    "13162": "Emblem Health (GHI/HIP)",
    "22773": "MVP Health Care",
    "14163": "Capital District Physicians HP",
    "80705": "Independent Health",
    "81578": "Geisinger Health Plan",
    "52192": "UPMC Health Plan",
    "54154": "AmeriHealth Caritas",
    "54155": "Priority Health",
    "38217": "HAP (Health Alliance Plan)",
    "38218": "Blue Care Network (MI)",
    "41076": "Medical Mutual of Ohio",
    "65088": "CareSource",
    "77350": "Paramount Health Care",
    "23282": "Meridian Health Plan",
    "63045": "Buckeye Health Plan",
    "59065": "Prestige Health Choice",
    "95378": "AvMed",
    "59064": "Simply Healthcare",
    "59066": "Sunshine Health",
    "95688": "Devoted Health",
    "95689": "Clover Health",
    "95690": "Oscar Health",
    "95691": "Oscar Health - NY",
    "95692": "Oscar Health - TX",
    "95693": "Oscar Health - CA",
    "95694": "Friday Health Plans",
    "44054": "SelectHealth",
    "77010": "Deseret Mutual",
    "44832": "DMBA",
    "81400": "Sanford Health Plan",
    "81401": "Avera Health Plans",
    "99109": "Quartz Health Solutions",
    "99110": "Group Health Cooperative (WI)",
    "39064": "PreferredOne",
    "45187": "HealthPartners",
    "39065": "UCare",
    "45188": "Medica",
    "45189": "Blue Plus (MN)",
    "31441": "Scott and White Health Plan",
    "31442": "Community Health Choice (TX)",
    "31443": "Driscoll Health Plan",
    "31444": "Superior HealthPlan",
    "31445": "El Paso First Health Plans",
    "31446": "Sendero Health Plans",
    "31447": "Community First Health Plans",
    "77034": "Louisiana Healthcare Connections",
    "77035": "Vantage Health Plan",
    "77036": "Gilsbar",
    "31600": "CHRISTUS Health Plan",
}

DENTAL_VISION_SPECIALTY = {
    "23045": "Delta Dental",
    "23046": "Delta Dental of CA",
    "23047": "Delta Dental of NY",
    "23048": "Delta Dental of TX",
    "23049": "Delta Dental of PA",
    "23050": "Delta Dental of MI",
    "23051": "Delta Dental of MN",
    "23052": "Delta Dental of WI",
    "23053": "Delta Dental of FL",
    "23054": "Delta Dental of OH",
    "23055": "Delta Dental of IL",
    "68035": "MetLife Dental",
    "68036": "MetLife Vision",
    "49182": "Guardian Life",
    "49183": "Guardian Dental",
    "85634": "VSP Vision",
    "85635": "EyeMed",
    "22240": "DentaQuest",
    "22241": "MCNA Dental",
    "22242": "Dental Health Alliance",
    "22243": "Dominion Dental",
    "85636": "March Vision Care",
    "85637": "Davis Vision",
    "85638": "Superior Vision",
    "94300": "Sun Life Financial",
    "94301": "Principal Financial",
    "94302": "Lincoln Financial",
    "94303": "Hartford Life",
    "94304": "Standard Insurance",
    "94305": "Unum",
    "94306": "Aflac",
    "94307": "Colonial Life",
    "94308": "Reliance Standard",
    "94309": "Transamerica",
}

MANAGED_MEDICAID_MCO = {
    "77001": "Amerigroup (Anthem)",
    "77002": "Amerigroup - GA",
    "77003": "Amerigroup - TX",
    "77004": "Amerigroup - NJ",
    "77005": "Amerigroup - TN",
    "77006": "Amerigroup - FL",
    "81890": "Buckeye Health Plan (Centene)",
    "34526": "CeltiCare Health Plan",
    "34527": "Absolute Total Care",
    "34528": "Peach State Health Plan",
    "34529": "Sunshine State Health Plan",
    "34530": "Home State Health (MO)",
    "34531": "NH Healthy Families",
    "34532": "Western Sky Community Care",
    "34533": "Oklahoma Complete Health",
    "34534": "Coordinated Care (WA)",
    "34535": "Trillium Community Health (OR)",
    "34536": "Health Net Federal Services",
    "34537": "Health Net of CA",
    "34538": "Health Net of AZ",
    "34539": "Managed Health Network",
    "34540": "Magellan Health",
    "34541": "Magellan Complete Care",
    "34542": "Beacon Health Options",
    "34543": "Optum Behavioral Health",
    "34544": "New Directions Behavioral",
    "34545": "Cenpatico Behavioral",
    "75085": "IlliniCare Health Plan",
    "75086": "Meridian Health Plan of IL",
    "75087": "Meridian Health Plan of MI",
    "75088": "Meridian Health Plan of IA",
    "75089": "Passport Health Plan (KY)",
    "75090": "Magnolia Health (MS)",
    "75091": "Granite State Health Plan",
    "75092": "SilverSummit Healthplan (NV)",
    "75093": "Sunshine Health Plan (FL)",
    "75094": "Pennsylvania Health & Wellness",
}

WORKERS_COMP_AUTO = {
    "WC001": "Travelers WC",
    "WC002": "Hartford WC",
    "WC003": "Liberty Mutual WC",
    "WC004": "Zurich WC",
    "WC005": "AIG WC",
    "WC006": "CNA WC",
    "WC007": "Sedgwick CMS",
    "WC008": "Gallagher Bassett",
    "WC009": "CorVel Corporation",
    "WC010": "Broadspire",
    "WC011": "CompManagement Health Systems",
    "WC012": "ICW Group",
    "WC013": "Zenith National Insurance",
    "WC014": "EMPLOYERS Holdings",
    "WC015": "Pinnacol Assurance",
    "WC016": "Texas Mutual Insurance",
    "WC017": "State Compensation Insurance Fund",
    "WC018": "SAIF Corporation",
    "WC019": "Ohio BWC",
    "WC020": "Washington L&I",
    "AU001": "GEICO",
    "AU002": "State Farm",
    "AU003": "Progressive",
    "AU004": "Allstate",
    "AU005": "USAA",
    "AU006": "Nationwide",
    "AU007": "Farmers Insurance",
    "AU008": "American Family Insurance",
    "AU009": "Erie Insurance",
    "AU010": "Auto-Owners Insurance",
}

MEDICARE_ADVANTAGE = {
    "H0028": "Aetna Medicare (PPO)",
    "H0543": "UHC Medicare Advantage HMO",
    "H1036": "Humana Gold Plus HMO",
    "H3312": "Kaiser Senior Advantage",
    "H5521": "Cigna-HealthSpring Preferred",
    "H5521A": "Cigna-HealthSpring TN",
    "R5826": "BCBS Medicare Advantage (PPO)",
    "H4091": "Devoted Health Medicare",
    "H9003": "Clover Health Medicare",
    "H2256": "WellCare Medicare Advantage",
    "H3954": "Centene Medicare",
    "H3113": "Molina Medicare HMO",
    "H5793": "Anthem Medicare Advantage",
    "H2406": "Highmark Medicare Advantage",
    "H7330": "Geisinger Gold Medicare",
    "H3949": "Capital Health Plan Medicare",
    "H1350": "AvMed Medicare Choice",
    "H1419": "CarePlus Health Plans",
    "H2012": "Florida Blue Medicare",
    "H1283": "Physicians Health Plan Medicare",
}

CHIP_PROGRAMS = {
    "ALCHP": "Alabama CHIP (ALL Kids)",
    "AKCHP": "Alaska CHIP (Denali KidCare)",
    "AZCHP": "Arizona CHIP (KidsCare)",
    "ARCHP": "Arkansas CHIP (ARKids First)",
    "CACHP": "California CHIP (Healthy Families)",
    "COCHP": "Colorado CHIP (CHP+)",
    "CTCHP": "Connecticut CHIP (HUSKY B)",
    "DECHP": "Delaware CHIP",
    "FLCHP": "Florida CHIP (KidCare)",
    "GACHP": "Georgia CHIP (PeachCare)",
    "HICHP": "Hawaii CHIP",
    "IDCHP": "Idaho CHIP",
    "ILCHP": "Illinois CHIP (All Kids)",
    "INCHP": "Indiana CHIP (Hoosier Healthwise)",
    "IACHP": "Iowa CHIP (hawk-i)",
    "KSCHP": "Kansas CHIP (HealthWave)",
    "KYCHP": "Kentucky CHIP (KCHIP)",
    "LACHP": "Louisiana CHIP (LaCHIP)",
    "MECHP": "Maine CHIP (CubCare)",
    "MDCHP": "Maryland CHIP",
    "MACHP": "Massachusetts CHIP (MassHealth)",
    "MICHP": "Michigan CHIP (MIChild)",
    "MNCHP": "Minnesota CHIP (MinnesotaCare)",
    "MSCHP": "Mississippi CHIP",
    "MOCHP": "Missouri CHIP (MC+)",
    "MTCHP": "Montana CHIP (Healthy MT Kids)",
    "NECHP": "Nebraska CHIP (Kids Connection)",
    "NVCHP": "Nevada CHIP (NCK)",
    "NHCHP": "New Hampshire CHIP (Healthy Kids)",
    "NJCHP": "New Jersey CHIP (FamilyCare)",
    "NMCHP": "New Mexico CHIP (NM Health)",
    "NYCHP": "New York CHIP (Child Health Plus)",
    "NCCHP": "North Carolina CHIP (Health Choice)",
    "NDCHP": "North Dakota CHIP (Healthy Steps)",
    "OHCHP": "Ohio CHIP (Healthy Start)",
    "OKCHP": "Oklahoma CHIP (SoonerCare)",
    "ORCHP": "Oregon CHIP (Healthy Kids)",
    "PACHP": "Pennsylvania CHIP",
    "RICHP": "Rhode Island CHIP (Rite Care)",
    "SCCHP": "South Carolina CHIP",
    "SDCHP": "South Dakota CHIP (CHIP)",
    "TNCHP": "Tennessee CHIP (CoverKids)",
    "TXCHP": "Texas CHIP (TexCare)",
    "UTCHP": "Utah CHIP",
    "VTCHP": "Vermont CHIP (Dr. Dynasaur)",
    "VACHP": "Virginia CHIP (FAMIS)",
    "WACHP": "Washington CHIP (Apple Health Kids)",
    "WVCHP": "West Virginia CHIP",
    "WICHP": "Wisconsin CHIP (BadgerCare Plus)",
    "WYCHP": "Wyoming CHIP (Kid Care CHIP)",
}

TPAs_AND_OTHERS = {
    "TP001": "Meritain Health (Aetna TPA)",
    "TP002": "HealthSCOPE Benefits",
    "TP003": "UMR (UHC TPA)",
    "TP004": "Cofinity (Aetna TPA)",
    "TP005": "Zelis Healthcare",
    "TP006": "Multiplan / PHCS",
    "TP007": "First Health (Coventry)",
    "TP008": "Three Rivers Provider Network",
    "TP009": "Beech Street (Multiplan)",
    "TP010": "CCN - Cigna",
    "TP011": "CoreSource",
    "TP012": "Allegiance Benefit Plan",
    "TP013": "ASR Health Benefits",
    "TP014": "Benefit Focus",
    "TP015": "Boon Group",
    "TP016": "Consolidated Health Plans",
    "TP017": "Custom Design Benefits",
    "TP018": "Employee Benefit Management",
    "TP019": "Friday Health Plans TPA",
    "TP020": "GPA (Group & Pension Admin)",
    "TP021": "HealthEZ",
    "TP022": "Key Benefit Administrators",
    "TP023": "LOOMIS Company",
    "TP024": "National Benefit Fund",
    "TP025": "Nippon Life Benefits",
    "TP026": "Pacific Source Health Plans",
    "TP027": "QualChoice Health Insurance",
    "TP028": "Rocky Mountain HMO",
    "TP029": "SAMBA Federal Plan",
    "TP030": "The Lewer Agency",
    "TP031": "Total Administrative Services",
    "TP032": "Trustmark Health Benefits",
    "TP033": "WebTPA",
    "TP034": "American Administrative Group",
    "TP035": "Benecard",
    "TP036": "Clarity Benefit Solutions",
    "TP037": "DataPath",
    "TP038": "EB Benefits",
    "TP039": "Group Resources",
    "TP040": "HealthMarket",
}

# Additional commercial plans to bulk up to ~2,200
ADDITIONAL_COMMERCIAL = {}

# Regional HMOs and PPOs
regional_names = [
    "Allina Health Plan", "Banner Health Plan", "Baystate Health",
    "BJC HealthCare Plan", "Carilion Health Plan", "Centura Health Plan",
    "Christiana Care Health Plan", "Community Care Alliance", "Community Health Network",
    "Cook County Health Plan", "Dean Health Plan", "Denver Health Medical Plan",
    "Essentia Health Plan", "Fairview Health Plan", "Gundersen Health Plan",
    "HonorHealth Plan", "Intermountain Health Plan", "Johns Hopkins Health Plan",
    "Lehigh Valley Health Plan", "Marshfield Clinic HP", "Mass General Brigham HP",
    "Mayo Clinic Health Plan", "Memorial Hermann HP", "Mercy Health Plan",
    "Methodist Health Plan", "Mount Sinai Health Plan", "Northwell Health Plan",
    "NovaStar Health", "OhioHealth Plan", "Ochsner Health Plan",
    "Orlando Health Plan", "OSF HealthCare Plan", "Parkview Health Plan",
    "Penn Medicine Health Plan", "Piedmont Health Plan", "ProHealth Network",
    "Providence Health Plan", "Rush Health Plan", "Sentara Health Plan",
    "Sharp Health Plan", "Spectrum Health Plan", "SSM Health Plan",
    "St. Luke's Health Plan", "Sutter Health Plan", "Texas Health Plan",
    "Trinity Health Plan", "Tufts Health Direct", "UCSF Health Plan",
    "Unity Health Plan", "UnityPoint Health Plan", "University Health Plan",
    "UTMB Health Plan", "Virtua Health Plan", "WakeMed Health Plan",
    "Yale New Haven Health Plan",
    # Marketplace / ACA Exchange Plans
    "Ambetter of Arkansas", "Ambetter of Florida", "Ambetter of Georgia",
    "Ambetter of Illinois", "Ambetter of Indiana", "Ambetter of Kansas",
    "Ambetter of Kentucky", "Ambetter of Louisiana", "Ambetter of Michigan",
    "Ambetter of Mississippi", "Ambetter of Missouri", "Ambetter of Nebraska",
    "Ambetter of Nevada", "Ambetter of New Hampshire", "Ambetter of New Jersey",
    "Ambetter of New Mexico", "Ambetter of North Carolina", "Ambetter of Ohio",
    "Ambetter of Oklahoma", "Ambetter of Pennsylvania", "Ambetter of South Carolina",
    "Ambetter of Tennessee", "Ambetter of Texas", "Ambetter of Virginia",
    "Ambetter of Washington", "Ambetter of Wisconsin",
    # Medicaid MCOs (additional)
    "Aetna Better Health of FL", "Aetna Better Health of IL", "Aetna Better Health of KY",
    "Aetna Better Health of LA", "Aetna Better Health of MD", "Aetna Better Health of MI",
    "Aetna Better Health of NJ", "Aetna Better Health of NY", "Aetna Better Health of OH",
    "Aetna Better Health of PA", "Aetna Better Health of TX", "Aetna Better Health of VA",
    "Aetna Better Health of WV",
    "UHC Community Plan of FL", "UHC Community Plan of GA", "UHC Community Plan of IA",
    "UHC Community Plan of KS", "UHC Community Plan of KY", "UHC Community Plan of LA",
    "UHC Community Plan of MD", "UHC Community Plan of MI", "UHC Community Plan of MS",
    "UHC Community Plan of NC", "UHC Community Plan of NE", "UHC Community Plan of NJ",
    "UHC Community Plan of NY", "UHC Community Plan of OH", "UHC Community Plan of PA",
    "UHC Community Plan of RI", "UHC Community Plan of TN", "UHC Community Plan of TX",
    "UHC Community Plan of VA", "UHC Community Plan of WI",
    # Self-funded employer plans (common large employers)
    "Walmart Employee Health Plan", "Amazon Employee Health Plan",
    "Apple Employee Health Plan", "Google Employee Health Plan",
    "Microsoft Employee Health Plan", "JPMorgan Chase Health Plan",
    "Bank of America Health Plan", "Wells Fargo Health Plan",
    "Citigroup Health Plan", "AT&T Employee Health Plan",
    "Verizon Employee Health Plan", "General Motors Health Plan",
    "Ford Motor Health Plan", "Boeing Employee Health Plan",
    "Lockheed Martin Health Plan", "Raytheon Health Plan",
    "Northrop Grumman Health Plan", "General Dynamics Health Plan",
    "FedEx Employee Health Plan", "UPS Employee Health Plan",
    "Caterpillar Health Plan", "John Deere Health Plan",
    "3M Employee Health Plan", "General Electric Health Plan",
    "Honeywell Health Plan", "Procter & Gamble Health Plan",
    "Johnson & Johnson Health Plan", "Pfizer Employee Health Plan",
    "IBM Employee Health Plan", "Intel Employee Health Plan",
    "Coca-Cola Employee Health Plan", "PepsiCo Employee Health Plan",
    "Target Employee Health Plan", "Costco Employee Health Plan",
    "Home Depot Employee Health Plan", "Lowes Employee Health Plan",
    "Kroger Employee Health Plan", "CVS Health Employee Plan",
    "Disney Employee Health Plan", "Comcast Employee Health Plan",
    # Health sharing ministries & alternative plans
    "Medi-Share", "Samaritan Ministries", "Christian Healthcare Ministries",
    "Liberty HealthShare", "Aliera Healthcare", "Sedera Health",
    # Pharmacy Benefit Managers (medical claims)
    "Express Scripts", "Caremark (CVS)", "OptumRx",
    "MedImpact Healthcare Systems", "Envolve Pharmacy Solutions",
    "Navitus Health Solutions", "Elixir Solutions",
    "Prime Therapeutics", "Magellan Rx Management",
    # Behavioral Health Carveouts
    "Optum Behavioral - East", "Optum Behavioral - West",
    "Beacon Health - Northeast", "Beacon Health - Southeast",
    "Beacon Health - Central", "Beacon Health - Western",
    "Cenpatico - Southwest", "Cenpatico - Southeast",
    # Supplemental / Indemnity
    "Aflac Supplemental", "Colonial Penn", "Globe Life",
    "Mutual of Omaha", "American Fidelity", "Starmount Life",
    "Combined Insurance", "Allstate Benefits", "MetLife Supplemental",
    "Cigna Supplemental", "Transamerica Supplemental",
    # International / Travel
    "GeoBlue (BCBS International)", "Cigna Global Health Benefits",
    "UHC Global", "Aetna International",
    "IMG (International Medical Group)", "Seven Corners",
    "Allianz Travel Insurance", "HTH Worldwide",
    # Additional state Medicaid managed care
    "Anthem Medicaid - CA", "Anthem Medicaid - IN", "Anthem Medicaid - KY",
    "Anthem Medicaid - OH", "Anthem Medicaid - VA", "Anthem Medicaid - WI",
    "Molina Medicaid - CA", "Molina Medicaid - FL", "Molina Medicaid - IL",
    "Molina Medicaid - MI", "Molina Medicaid - NM", "Molina Medicaid - NY",
    "Molina Medicaid - OH", "Molina Medicaid - SC", "Molina Medicaid - TX",
    "Molina Medicaid - UT", "Molina Medicaid - WA", "Molina Medicaid - WI",
    "WellCare Medicaid - FL", "WellCare Medicaid - GA", "WellCare Medicaid - IL",
    "WellCare Medicaid - KY", "WellCare Medicaid - LA", "WellCare Medicaid - MI",
    "WellCare Medicaid - MS", "WellCare Medicaid - MO", "WellCare Medicaid - NE",
    "WellCare Medicaid - NJ", "WellCare Medicaid - NY", "WellCare Medicaid - OH",
    "WellCare Medicaid - TX",
    # Stand-alone Medicare Part D plans
    "SilverScript (CVS)", "AARP MedicareRx (UHC)", "Humana Walmart Rx",
    "Cigna Extra Rx", "WellCare Classic PDP", "Elixir PDP",
    "Envision Rx Plus PDP", "InfuSystem PDP",
    # Small-state and niche plans
    "Community Health Options (ME)", "Minuteman Health (MA)",
    "Neighborhood Health Plan (RI)", "Neighborhood Health Plan (MA)",
    "Network Health Plan (WI)", "Health Plan of Nevada",
    "SilverSummit Healthplan (NV)", "Health Plan of San Joaquin",
    "Health Plan of San Mateo", "Partnership HealthPlan (CA)",
    "LA Care Health Plan", "CalOptima", "Inland Empire HP",
    "Kern Health Systems", "Santa Clara Family HP",
    "San Francisco Health Plan", "Gold Coast Health Plan",
    "Central California Alliance", "Contra Costa Health Plan",
    "Health Net Community Solutions",
    # Miscellaneous carriers
    "American Republic Insurance", "American National Insurance",
    "Bankers Life and Casualty", "Conseco Health Insurance",
    "Freedom Life Insurance", "Gerber Life Insurance",
    "Golden Rule Insurance", "HealthMarkets",
    "Individual Assurance Company", "John Alden Life Insurance",
    "LifeWise Health Plan", "Medica Health Plans",
    "National Western Life Insurance", "Oxford Health Plans",
    "PacificSource Health Plans", "Premera Blue Cross",
    "Regence BlueCross BlueShield", "Security Benefit Life",
    "State Auto Financial", "Starmark Life Insurance",
    "Trustmark Insurance", "United American Insurance",
    "World Financial Group", "Zurich American Insurance",
]

base_id = 30000
for name in regional_names:
    pid = str(base_id)
    ADDITIONAL_COMMERCIAL[pid] = name
    base_id += 1

# ── Programmatic bulk generation to reach ~2,200 total ────────────────────────
# Generate plausible payer names across several categories

_states = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

_state_names = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

# County-based health plans (realistic pattern in CA, NY, FL, TX, etc.)
_county_names = [
    "Alameda", "Contra Costa", "Fresno", "Kings", "Los Angeles", "Madera",
    "Marin", "Merced", "Monterey", "Orange", "Riverside", "Sacramento",
    "San Bernardino", "San Diego", "San Francisco", "San Joaquin",
    "San Luis Obispo", "San Mateo", "Santa Barbara", "Santa Clara",
    "Santa Cruz", "Solano", "Sonoma", "Stanislaus", "Tulare", "Ventura",
    "Yolo", "Cook", "DuPage", "Lake", "Will", "Kane", "McHenry",
    "Broward", "Miami-Dade", "Palm Beach", "Hillsborough", "Pinellas",
    "Duval", "Polk", "Brevard", "Volusia", "Seminole", "Osceola",
    "Harris", "Dallas", "Tarrant", "Bexar", "Travis", "Collin",
    "Denton", "El Paso", "Hidalgo", "Fort Bend",
    "Maricopa", "Pima", "Clark", "Washoe", "King", "Pierce",
    "Snohomish", "Multnomah", "Wayne", "Oakland", "Macomb",
    "Hennepin", "Ramsey", "Cuyahoga", "Franklin", "Hamilton",
    "Marion", "Hamilton", "Suffolk", "Nassau", "Westchester",
    "Erie", "Monroe", "Allegheny", "Philadelphia", "Montgomery",
    "Bucks", "Chester", "Delaware",
]

_health_system_prefixes = [
    "Ascension", "CommonSpirit", "HCA", "Tenet", "AdventHealth",
    "Atrium", "Baylor Scott & White", "Beaumont", "Bon Secours Mercy",
    "Cedars-Sinai", "ChristianaCare", "Cleveland Clinic", "Duke",
    "Emory", "Hackensack Meridian", "Henry Ford", "Houston Methodist",
    "IU Health", "Mass General Brigham", "MedStar", "Memorial Sloan Kettering",
    "Mercy", "Mount Sinai", "NewYork-Presbyterian", "Northwestern Medicine",
    "Novant", "NYU Langone", "OhioHealth", "Orlando Health",
    "Piedmont", "Providence", "Rush", "SCL Health", "Scripps",
    "Sutter", "UCSF", "UCLA", "UNC Health", "UnityPoint",
    "UPMC", "Vanderbilt", "Wake Forest Baptist", "WellSpan",
    "Yale New Haven", "Advocate Aurora", "Ballad Health",
    "Baptist Health", "Centura", "Children's National",
    "Dignity Health", "Froedtert", "Gundersen", "Hartford HealthCare",
    "Inova", "Intermountain", "Johns Hopkins", "Lehigh Valley",
    "MaineHealth", "McLaren", "Methodist", "Nuvance",
    "Penn State Health", "Prisma Health", "Renown Health",
    "RWJBarnabas", "Sanford", "Sharp", "Spectrum Health",
    "St. Joseph", "St. Vincent", "Stanford Health Care",
    "Tampa General", "Virtua", "WakeMed",
]

_union_names = [
    "SEIU", "AFSCME", "Teamsters", "UAW", "IBEW", "CWA",
    "Steelworkers", "Machinists", "Carpenters", "Plumbers & Pipefitters",
    "Painters", "Laborers", "Operating Engineers", "Sheet Metal Workers",
    "Bricklayers", "Ironworkers", "Boilermakers", "Firefighters",
    "Police Officers", "Teachers (NEA)", "Teachers (AFT)",
    "Postal Workers (APWU)", "Letter Carriers (NALC)", "Mail Handlers",
    "Government Employees (AFGE)", "Transit Workers (ATU)",
    "Communications Workers", "Electrical Workers", "Food & Commercial (UFCW)",
    "Hotel & Restaurant (UNITE HERE)",
]

_employer_types = [
    "Municipal Employee HP", "County Employee HP", "State Employee HP",
    "School District HP", "University Employee HP",
    "Hospital Employee HP", "Transit Authority HP",
    "Port Authority HP", "Water District HP", "Fire District HP",
]

# Build additional entries
_gen_id = base_id  # continue from where regional_names left off

# 1) County health plans (~80)
for county in _county_names:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{county} County Health Plan"
    _gen_id += 1

# 2) Health system employee plans (~72)
for hs in _health_system_prefixes:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{hs} Employee Health Plan"
    _gen_id += 1

# 3) Union health funds (~30)
for union in _union_names:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{union} Health & Welfare Fund"
    _gen_id += 1

# 4) State employee / public sector plans (50 states x 2 = 100)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} State Employee Health Plan"
    _gen_id += 1
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Public School Employee HP"
    _gen_id += 1

# 5) Regional IPA / physician group plans (~50 states)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Physicians IPA"
    _gen_id += 1

# 6) State-specific ACA CO-OP and marketplace remnants (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Health CO-OP"
    _gen_id += 1

# 7) Hospital indemnity / accident plans (per state, ~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Hospital Indemnity Plan"
    _gen_id += 1

# 8) Cigna state affiliates (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"Cigna Health Plan of {st_name}"
    _gen_id += 1

# 9) Humana state affiliates (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"Humana Health Plan of {st_name}"
    _gen_id += 1

# 10) Aetna state affiliates (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"Aetna Health Plan of {st_name}"
    _gen_id += 1

# 11) UHC state affiliates (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"UnitedHealthcare of {st_name}"
    _gen_id += 1

# 12) Municipal / public-sector employer types per large state (~80)
_large_states = [
    "California", "Texas", "Florida", "New York", "Pennsylvania",
    "Illinois", "Ohio", "Georgia", "Michigan", "North Carolina",
]
for ls in _large_states:
    for et in _employer_types:
        ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{ls} {et}"
        _gen_id += 1

# 13) More Medicare Advantage contract IDs (~100)
_ma_prefixes = ["H", "R", "S", "E"]
_ma_counter = 6000
for prefix in _ma_prefixes:
    for i in range(25):
        ma_id = f"{prefix}{_ma_counter + i:04d}"
        if ma_id not in ADDITIONAL_COMMERCIAL:
            ADDITIONAL_COMMERCIAL[ma_id] = f"Medicare Advantage Plan {ma_id}"

# 14) Kaiser state affiliates (~20)
_kaiser_states = [
    "California (N)", "California (S)", "Colorado", "Georgia", "Hawaii",
    "Maryland", "Oregon", "Virginia", "Washington", "DC",
    "Mid-Atlantic", "Northwest", "Northern CA", "Southern CA",
    "Central Valley CA", "Inland Empire CA", "San Diego CA",
    "Denver CO", "Atlanta GA", "Portland OR",
]
for ks in _kaiser_states:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"Kaiser Permanente - {ks}"
    _gen_id += 1

# 15) BCBS FEP variants per region (~30)
_bcbs_regions = [
    "Northeast", "Southeast", "Midwest", "Southwest", "West Coast",
    "Mid-Atlantic", "New England", "Great Lakes", "Plains",
    "Mountain", "Pacific Northwest", "Gulf Coast", "Appalachian",
    "Capital Region", "Tri-State",
]
for region in _bcbs_regions:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"BCBS {region} PPO"
    _gen_id += 1
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"BCBS {region} HMO"
    _gen_id += 1

# 16) Managed behavioral health per state (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Behavioral Health Plan"
    _gen_id += 1

# 17) Dental / Vision per-state expansions (~100)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"Delta Dental of {st_name}"
    _gen_id += 1
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"VSP of {st_name}"
    _gen_id += 1

# 18) Additional Workers Comp state funds (~40)
for st, st_name in zip(_states[:40], _state_names[:40]):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Workers Comp State Fund"
    _gen_id += 1

# 19) University / college student health plans (~40)
_universities = [
    "Harvard", "MIT", "Stanford", "Yale", "Princeton",
    "Columbia", "Penn", "Cornell", "Brown", "Dartmouth",
    "Duke", "Johns Hopkins", "Northwestern", "Chicago",
    "Michigan", "Berkeley", "UCLA", "Virginia", "Georgetown",
    "Notre Dame", "Emory", "Vanderbilt", "Rice", "Tulane",
    "USC", "NYU", "Boston University", "Tufts", "Brandeis",
    "Carnegie Mellon", "Georgia Tech", "Purdue", "Ohio State",
    "Penn State", "Texas A&M", "Wisconsin", "Minnesota",
    "Iowa", "Illinois", "Indiana",
]
for uni in _universities:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{uni} Student Health Plan"
    _gen_id += 1

# 20) Auto insurance medical PIP per state (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{st_name} Auto PIP Medical"
    _gen_id += 1

# 21) Regional PPO networks (~30)
_ppo_networks = [
    "First Health PPO", "Multiplan PPO", "PHCS PPO", "Beech Street PPO",
    "Three Rivers PPO", "CCN PPO", "HealthSmart PPO", "National Preferred PPO",
    "Coventry PPO", "Galaxy Health Network", "USA Managed Care",
    "Interplan Health Group", "Evolutions Healthcare PPO",
    "GHP PPO Network", "MedCost PPO", "Cofinity PPO",
    "HealthLink PPO", "Focus PPO", "Stratose PPO",
    "NOVA Healthcare PPO", "Allied Benefit Systems PPO",
    "Benefit Management Group PPO", "National Health Plan PPO",
    "NovaSys Health PPO", "Pacific Health Alliance PPO",
    "Preferred Health Care PPO", "Southwest Service PPO",
    "United Benefit Advisors PPO", "Western Growers PPO",
    "Windsor Health Group PPO",
]
for name in _ppo_networks:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1

# 22) Correctional / incarcerated healthcare (~20)
_correctional = [
    "Centurion Health (East)", "Centurion Health (West)",
    "Centurion Health (South)", "Centurion Health (Midwest)",
    "Corizon Health (East)", "Corizon Health (West)",
    "Corizon Health (South)", "Corizon Health (Midwest)",
    "NaphCare (Southeast)", "NaphCare (Northeast)",
    "NaphCare (Central)", "NaphCare (Western)",
    "Wexford Health Sources (East)", "Wexford Health Sources (West)",
    "Armor Correctional Health (FL)", "Armor Correctional Health (NY)",
    "PrimeCare Medical (PA)", "PrimeCare Medical (NJ)",
    "Wellpath (Southeast)", "Wellpath (Central)",
]
for name in _correctional:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1

# 23) Tribal / IHS health plans (~25)
_tribal_plans = [
    "Navajo Nation Health Plan", "Cherokee Nation Health",
    "Chickasaw Nation Health Plan", "Choctaw Nation Health",
    "Creek Nation Health Plan", "Seminole Nation Health",
    "Osage Nation Health Plan", "Apache Tribe Health Plan",
    "Blackfeet Tribe Health", "Crow Tribe Health Plan",
    "Sioux Nation Health Plan", "Pueblo Health Plan",
    "Tohono O'odham Health", "Gila River Health Plan",
    "Salt River Pima Health", "Yakama Nation Health",
    "Tulalip Tribes Health", "Muckleshoot Health Plan",
    "Lummi Nation Health", "Quinault Nation Health",
    "Chippewa Health Plan", "Oneida Nation Health",
    "Mohawk Council Health", "Seneca Nation Health",
    "Poarch Creek Health Plan",
]
for name in _tribal_plans:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1

# 24) Military / DOD supplemental (~15)
_mil_supplemental = [
    "Tricare Prime Remote", "Tricare Select",
    "Tricare Reserve Select", "Tricare Retired Reserve",
    "Tricare Young Adult", "Tricare Dental (ADDP)",
    "US Family Health Plan - Johns Hopkins",
    "US Family Health Plan - Martin's Point",
    "US Family Health Plan - Brighton Marine",
    "US Family Health Plan - St. Vincent Catholic",
    "US Family Health Plan - CHRISTUS",
    "US Family Health Plan - Pacific",
    "DOD Civilian Health Benefits", "Coast Guard Health Plan",
    "National Guard Health Plan",
]
for name in _mil_supplemental:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1

# 25) Faith-based / religious organization plans (~15)
_faith_plans = [
    "Catholic Health Initiatives Plan", "Adventist Health System Plan",
    "Baptist Health Plan (FL)", "Baptist Health Plan (AR)",
    "Baptist Health Plan (KY)", "Methodist Health Plan (TX)",
    "Methodist Health Plan (NE)", "Presbyterian Health Plan",
    "Trinity Health Plan (MI)", "Trinity Health Plan (ID)",
    "Mercy Health Plan (MO)", "Mercy Health Plan (OH)",
    "St. Joseph Health Plan", "Providence Health Plan (OR)",
    "Providence Health Plan (WA)",
]
for name in _faith_plans:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1

# 26) Additional employer self-funded (Fortune 500 tail) (~50)
_more_employers = [
    "Starbucks", "Nike", "Costco Wholesale", "Netflix",
    "Salesforce", "Oracle", "Cisco Systems", "Adobe",
    "Texas Instruments", "Qualcomm", "Broadcom", "AMD",
    "Nvidia", "Micron Technology", "Applied Materials",
    "Lam Research", "KLA Corporation", "Synopsys",
    "Cadence Design", "ServiceNow", "Workday",
    "Palo Alto Networks", "CrowdStrike", "Fortinet",
    "Zscaler", "Datadog", "Snowflake", "Palantir",
    "Uber", "Lyft", "DoorDash", "Airbnb",
    "PayPal", "Block (Square)", "Stripe",
    "Visa", "Mastercard", "American Express",
    "Goldman Sachs", "Morgan Stanley", "BlackRock",
    "Charles Schwab", "Fidelity Investments", "Vanguard",
    "State Street", "Northern Trust", "BNY Mellon",
    "Capital One", "Discover Financial", "Synchrony",
]
for emp in _more_employers:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"{emp} Employee Health Plan"
    _gen_id += 1

# 27) Multiplan / rental network variants per state (~50)
for st, st_name in zip(_states, _state_names):
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = f"Multiplan Network - {st_name}"
    _gen_id += 1

# 28) Managed long-term care / PACE programs (~40)
_ltc_plans = [
    "PACE of Central PA", "PACE of Philadelphia",
    "PACE of South FL", "PACE of North FL",
    "PACE of Chicago", "PACE of Detroit",
    "PACE of Los Angeles", "PACE of San Francisco",
    "PACE of Denver", "PACE of Seattle",
    "PACE of Portland", "PACE of Phoenix",
    "PACE of Boston", "PACE of Hartford",
    "PACE of Richmond", "PACE of Charlotte",
    "PACE of Atlanta", "PACE of Nashville",
    "PACE of Memphis", "PACE of St. Louis",
    "PACE of Kansas City", "PACE of Minneapolis",
    "PACE of Milwaukee", "PACE of Indianapolis",
    "PACE of Columbus", "PACE of Cleveland",
    "PACE of Pittsburgh", "PACE of Buffalo",
    "PACE of Albany", "PACE of Newark",
    "PACE of Trenton", "PACE of Baltimore",
    "PACE of DC", "PACE of Raleigh",
    "PACE of Charleston", "PACE of Jacksonville",
    "PACE of Tampa", "PACE of Orlando",
    "PACE of Houston", "PACE of Dallas",
]
for name in _ltc_plans:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1

# 29) Additional small / niche carriers (~80)
_niche_carriers = [
    "Access Health CT", "Alignment Healthcare", "AultCare",
    "AvantGuard Health Plan", "Berkshire Health Systems HP",
    "Bravo Health (now Cigna)", "Capital Blue Cross",
    "CareFirst BlueCross BlueShield", "CeltiCare Health",
    "Chinese Community HP", "CHRISTUS Health Plan (TX)",
    "Colorado Access", "CommunityCare (OK)", "ConnectiCare Benefits",
    "Coventry Health Care", "Dean Health Insurance",
    "EmblemHealth VIP", "Empire BlueCross BlueShield",
    "Envision Insurance", "EqualityCare (WY)", "Fallon Health",
    "FirstCare Health Plans (TX)", "Gateway Health",
    "Geisinger Quality Options", "Group Health Cooperative (WA)",
    "GuildNet", "HAP Senior Plus", "Health First (FL)",
    "Health New England", "Health Plan of Carrollton (TX)",
    "HealthFirst (NY)", "HealthNow NY", "HealthPlus Amerigroup",
    "Hennepin Health (MN)", "Horizon NJ Health",
    "IEHP (Inland Empire Health Plan)", "Independent Care Health Plan",
    "KelseyCare Advantage (TX)", "Kern Family Health Care",
    "Martin's Point Health Care (ME)", "MassHealth MCO",
    "McLaren Health Advantage", "Medical Associates Health Plan",
    "MedMutual", "Mercy Care Plan (AZ)", "MetroPlus Health Plan (NYC)",
    "MinnesotaCare", "Montana Health CO-OP",
    "Mountain Health CO-OP", "MVPIC", "National General Health",
    "New Era Life Insurance", "NHP (Neighborhood Health Plan)",
    "North Shore-LIJ CareConnect", "OhioHealth Insurance",
    "Paramount Advantage", "Parkland Community Health Plan",
    "PeachState Health Plan", "PHP (Physicians Health Plan MI)",
    "Point32Health", "Presbyterian Health Plan (NM)",
    "ProMedica Health Plan", "Quartz Health Plan",
    "Scott & White Health Plan", "Scion Health Plan",
    "SelectCare of Texas", "SmartHealth (WA)",
    "SoloCare Health Plan", "Soundpath Health",
    "SummaCare (OH)", "Sunrise Health Plan",
    "Today's Options (IN)", "Total Health Care (MI)",
    "Trillium Health Plan (OR)", "Triple-S Salud (PR)",
    "Tufts Medicare Preferred", "UCare Medicare",
    "University Health Alliance (HI)", "VIVA Health (AL)",
    "Wellfleet Student Health", "Western Health Advantage (CA)",
]
for name in _niche_carriers:
    ADDITIONAL_COMMERCIAL[str(_gen_id)] = name
    _gen_id += 1


# ── Route generation ──────────────────────────────────────────────────────────

random.seed(42)  # deterministic output


def make_routes(payer_id: str, num_routes: int | None = None) -> list[dict]:
    """Generate 1-3 routes for a payer, picking clearinghouses weighted by realism."""
    if num_routes is None:
        # Most payers have 2 routes; some have 1 or 3
        num_routes = random.choices([1, 2, 3], weights=[20, 55, 25])[0]

    # Weighted CH selection: change has broadest support so appears often as primary
    weights = {
        "change": 30,
        "availity": 25,
        "waystar": 20,
        "stedi": 15,
        "claimmd": 10,
    }

    # Pick distinct clearinghouses
    selected: list[str] = []
    pool = list(CH_NAMES)
    w = [weights[c] for c in pool]
    for _ in range(min(num_routes, len(pool))):
        ch = random.choices(pool, weights=w, k=1)[0]
        selected.append(ch)
        idx = pool.index(ch)
        pool.pop(idx)
        w.pop(idx)

    routes = []
    for priority, ch in enumerate(selected, start=1):
        ch_payer_id = payer_id  # default: same ID at the clearinghouse
        # Sometimes clearinghouses use their own mapped IDs
        if ch in ("stedi", "claimmd") and random.random() < 0.3:
            ch_payer_id = f"{ch.upper()[:3]}_{payer_id}"

        routes.append(
            {
                "clearinghouse": ch,
                "payer_id_at_clearinghouse": ch_payer_id,
                "priority": priority,
                "supports": list(CLEARINGHOUSES[ch]["supports"]),
            }
        )
    return routes


def build_routing_data() -> dict:
    """Assemble the full payer routing dictionary."""
    data: dict[str, list[dict]] = {}

    all_payers: dict[str, str] = {}
    all_payers.update(MEDICARE_PAYERS)
    all_payers.update(MEDICAID_PAYERS)
    all_payers.update(MAJOR_COMMERCIAL)
    all_payers.update(BCBS_AFFILIATES)
    all_payers.update(GOVERNMENT_MILITARY)
    all_payers.update(REGIONAL_PLANS)
    all_payers.update(DENTAL_VISION_SPECIALTY)
    all_payers.update(MANAGED_MEDICAID_MCO)
    all_payers.update(WORKERS_COMP_AUTO)
    all_payers.update(MEDICARE_ADVANTAGE)
    all_payers.update(CHIP_PROGRAMS)
    all_payers.update(TPAs_AND_OTHERS)
    all_payers.update(ADDITIONAL_COMMERCIAL)

    for payer_id, _name in all_payers.items():
        data[payer_id] = make_routes(payer_id)

    return data


def main() -> None:
    data = build_routing_data()

    out = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    json_bytes = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
    with gzip.open(out, "wb") as f:
        f.write(json_bytes)

    file_size = os.path.getsize(out)
    total_routes = sum(len(v) for v in data.values())

    print(f"Payer count   : {len(data):,}")
    print(f"Total routes  : {total_routes:,}")
    print(f"JSON size     : {len(json_bytes):,} bytes")
    print(f"Gzip size     : {file_size:,} bytes")
    print(f"Written to    : {out}")


if __name__ == "__main__":
    main()
