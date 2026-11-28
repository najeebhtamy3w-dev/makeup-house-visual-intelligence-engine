"""Independent provisional creative profiles; no invented brand assets."""
PROFILES={
    'makeup_house':{'name':'MAKEUP HOUSE','direction':'premium cosmetic editorial, clean studio lighting'},
    'unwan_al_atr':{'name':'عنوان العطر','direction':'premium fragrance editorial, refined atmospheric lighting'}
}
FORMATS={'square':(1080,1080),'story':(1080,1920),'portrait':(1080,1350)}
def campaign_prompt(brand,instruction):
    if brand not in PROFILES: raise ValueError('UNKNOWN_BRAND')
    if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>1500: raise ValueError('INVALID_INSTRUCTION')
    return PROFILES[brand]['direction']+'. '+instruction+'. Preserve original product packaging, label, logo and proportions. Do not invent product claims.'
