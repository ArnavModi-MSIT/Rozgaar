"""Career display configuration. Restart the server after edits."""
import re

DISPLAY_NAMES = {
    "deshaw": "D. E. Shaw India",
    "quadeye": "Quadeye",
    "rippling": "Rippling",
    "PHONEPELIMITED": "PhonePe",
    "towerresearchcapital": "Tower Research Capital",
    "gravitonresearchcapital": "Graviton Research Capital LLP",
    "goldman_sachs": "Goldman Sachs",  # .title() would give "Goldman_Sachs"
    "morganstanley": "Morgan Stanley",  # .title() would give "Morganstanley"
    "indiamart": "IndiaMART",  # .title() would give "Indiamart"
    "deutsche_bank": "Deutsche Bank",  # .title() would give "Deutsche_Bank"
    "standardchartered": "Standard Chartered",  # .title() would give "Standardchartered"
    "paloaltonetworks": "Palo Alto Networks",  # .title() would give "Paloaltonetworks"
    "phonepe": "PhonePe",
    "cred": "CRED",
    "roku":"Roku", "gleanwork":"Glean", "okta":"Okta", "purestorage":"Pure Storage",
    "gitlab":"GitLab", "squarepointcapital":"Squarepoint Capital",
    "quberesearchandtechnologies":"Qube Research & Technologies",
    "crowdstrike":"CrowdStrike", "broadcom":"Broadcom", "cohesity":"Cohesity",
    "postman":"Postman", "netflix":"Netflix", "automattic":"Automattic", "zerodha":"Zerodha",
    "alphagrepsecurities": "AlphaGrep",
    "nksecuritiesresearch": "NK Securities Research",
    "worldquant": "WorldQuant",
    "imc": "IMC",
    "optiverus": "Optiver",
    "mongodb": "MongoDB",
    "datadog": "Datadog",
    "amd": "AMD",
    "mediatek": "MediaTek",
    "tesco": "Tesco",
    "booking": "Booking.com",
    "juspay": "Juspay",
    "millennium": "Millennium",
    "paypal": "PayPal",
    "blackrock": "BlackRock",
    "expedia": "Expedia Group",
    "amex": "American Express",
    "jpmc": "JPMorgan Chase",
    "bcg": "Boston Consulting Group",
    "fidelity": "Fidelity International",
    "zs": "ZS Associates",
    "thoughtworks": "Thoughtworks",
    "zeta": "Zeta",
    "fractal": "Fractal Analytics",
    "Freshworks": "Freshworks",
    "servicenow": "ServiceNow",
    "salesforce": "Salesforce",
    "arcesiumllc": "Arcesium",
    "intuit": "Intuit",
    "nvidia": "NVIDIA",  # .title() would give "Nvidia" — wrong branding
    "BoschGroup": "Bosch",  # .title() on a no-space slug just capitalizes
                             # the first letter ("Boschgroup") — wrong
    "payu": "PayU",  # .title() would give "Payu" — wrong branding
    "spglobal": "S&P Global",  # .title() would give "Spglobal"
    "hp": "HP",  # .title() would give "Hp" — wrong branding
}
