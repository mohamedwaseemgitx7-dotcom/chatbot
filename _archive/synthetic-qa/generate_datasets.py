# -*- coding: utf-8 -*-
"""
Generates two CSV datasets for a Tamil Nadu farmer chatbot:
  1. tn_farmer_chats.csv   - 10,000 crop / farming / small-talk Q&A rows
  2. tn_farmer_schemes.csv - 10,000 government-scheme Q&A rows
Each row is in one language: ta (Tamil script), en (English), tanglish (Tamil in Latin script).
The answer is always in the same language as the question.

Rows are template-generated (synthetic). Facts are approximate/general;
verify scheme amounts and rules on the official sources before production use.
"""
import csv, random, re, itertools
from collections import defaultdict

random.seed(42)
TARGET = 10_000
LANGS = ["ta", "en", "tanglish"]

# ---------------------------------------------------------------- districts
DISTRICTS = [
    ("Thanjavur", "தஞ்சாவூர்"), ("Tiruvarur", "திருவாரூர்"), ("Nagapattinam", "நாகப்பட்டினம்"),
    ("Mayiladuthurai", "மயிலாடுதுறை"), ("Trichy", "திருச்சி"), ("Madurai", "மதுரை"),
    ("Coimbatore", "கோயம்புத்தூர்"), ("Erode", "ஈரோடு"), ("Salem", "சேலம்"), ("Namakkal", "நாமக்கல்"),
    ("Dindigul", "திண்டுக்கல்"), ("Theni", "தேனி"), ("Tirunelveli", "திருநெல்வேலி"),
    ("Thoothukudi", "தூத்துக்குடி"), ("Virudhunagar", "விருதுநகர்"), ("Villupuram", "விழுப்புரம்"),
    ("Cuddalore", "கடலூர்"), ("Kanchipuram", "காஞ்சிபுரம்"), ("Vellore", "வேலூர்"),
    ("Tiruvannamalai", "திருவண்ணாமலை"), ("Krishnagiri", "கிருஷ்ணகிரி"), ("Dharmapuri", "தர்மபுரி"),
    ("Pudukkottai", "புதுக்கோட்டை"), ("Sivaganga", "சிவகங்கை"), ("Ramanathapuram", "ராமநாதபுரம்"),
    ("Karur", "கரூர்"), ("Perambalur", "பெரம்பலூர்"), ("Ariyalur", "அரியலூர்"),
    ("Kanyakumari", "கன்னியாகுமரி"), ("Tiruppur", "திருப்பூர்"), ("Nilgiris", "நீலகிரி"),
    ("Kallakurichi", "கள்ளக்குறிச்சி"), ("Tenkasi", "தென்காசி"), ("Chengalpattu", "செங்கல்பட்டு"),
    ("Ranipet", "ராணிப்பேட்டை"), ("Tirupathur", "திருப்பத்தூர்"), ("Tiruvallur", "திருவள்ளூர்"),
]

# ---------------------------------------------------------------- crops
# season / duration / common pests are approximate and vary by variety & district
CROPS = {
 "paddy": dict(
  en="paddy", ta="நெல்", tl="nel",
  season_en="In Tamil Nadu, paddy is grown in Kuruvai (June–September), Samba (August–January) and Thaladi/Navarai seasons.",
  season_ta="தமிழ்நாட்டில் நெல் குறுவை (ஜூன்–செப்டம்பர்), சம்பா (ஆகஸ்ட்–ஜனவரி), தாளடி/நவரை பருவங்களில் பயிரிடப்படுகிறது.",
  season_tl="Tamil Nadu la nel Kuruvai (June–September), Samba (August–January), Thaladi/Navarai season la podalaam.",
  dur_en="105 to 150 days depending on the variety", dur_ta="ரகத்தைப் பொறுத்து 105 முதல் 150 நாட்கள்", dur_tl="ragatha poruthu 105 la irundhu 150 naal",
  pest_en="stem borer and brown planthopper", pest_ta="தண்டு துளைப்பான் மற்றும் புகையான்", pest_tl="thandu thulaippan, pugaiyaan"),
 "banana": dict(
  en="banana", ta="வாழை", tl="vaazhai",
  season_en="Banana is commonly planted during February–April, and in some districts with the monsoon.",
  season_ta="வாழை பொதுவாக பிப்ரவரி–ஏப்ரல் மாதங்களில் நடப்படுகிறது; சில மாவட்டங்களில் பருவமழை காலத்திலும் நடலாம்.",
  season_tl="Vaazhai podhuva February–April la nadalaam; sila district la monsoon time layum nadalaam.",
  dur_en="11 to 14 months until bunch harvest", dur_ta="தார் அறுவடைக்கு 11 முதல் 14 மாதங்கள்", dur_tl="thaar aruvadaiku 11 la irundhu 14 maasam",
  pest_en="rhizome weevil and Sigatoka leaf spot", pest_ta="கிழங்கு கூன்வண்டு மற்றும் சிகடோகா இலைப்புள்ளி நோய்", pest_tl="kizhangu koon vandu, sigatoka ilai pulli noi"),
 "sugarcane": dict(
  en="sugarcane", ta="கரும்பு", tl="karumbu",
  season_en="Sugarcane is planted in the early season (December–January), mid season (February–March) and late season (April–May).",
  season_ta="கரும்பு முன்பருவம் (டிசம்பர்–ஜனவரி), நடுப்பருவம் (பிப்ரவரி–மார்ச்), பின்பருவம் (ஏப்ரல்–மே) ஆகியவற்றில் நடவு செய்யப்படுகிறது.",
  season_tl="Karumbu early season (December–January), mid season (February–March), late season (April–May) la nadavu pannalaam.",
  dur_en="10 to 12 months", dur_ta="10 முதல் 12 மாதங்கள்", dur_tl="10 la irundhu 12 maasam",
  pest_en="early shoot borer", pest_ta="இளம் குருத்துப் புழு", pest_tl="early shoot borer (kuruthu puzhu)"),
 "coconut": dict(
  en="coconut", ta="தென்னை", tl="thennai",
  season_en="Coconut seedlings are best planted at the start of the monsoon (June–July or September–October).",
  season_ta="தென்னங்கன்றுகளை பருவமழை தொடக்கத்தில் (ஜூன்–ஜூலை அல்லது செப்டம்பர்–அக்டோபர்) நடுவது நல்லது.",
  season_tl="Thennai kandru-va monsoon start la (June–July illa September–October) nadalaam.",
  dur_en="about 6–7 years to start bearing for tall varieties and about 3–4 years for hybrid/dwarf varieties",
  dur_ta="நெட்டை ரகங்கள் சுமார் 6–7 ஆண்டுகளிலும், வீரிய/குட்டை ரகங்கள் சுமார் 3–4 ஆண்டுகளிலும் காய்க்கத் தொடங்கும்",
  dur_tl="nettai ragam 6–7 varushathula, hybrid/kuttai ragam 3–4 varushathula kaaikka aarambikkum",
  pest_en="rhinoceros beetle and red palm weevil", pest_ta="காண்டாமிருக வண்டு மற்றும் சிவப்பு கூன்வண்டு", pest_tl="rhinoceros vandu, sivappu koon vandu"),
 "groundnut": dict(
  en="groundnut", ta="நிலக்கடலை", tl="nilakadalai",
  season_en="Groundnut is sown in June–July (rainfed) and December–January (irrigated).",
  season_ta="நிலக்கடலை ஜூன்–ஜூலை (மானாவாரி) மற்றும் டிசம்பர்–ஜனவரி (இறவை) மாதங்களில் விதைக்கப்படுகிறது.",
  season_tl="Nilakadalai June–July (maanaavaari), December–January (iravai) la vidhaikalaam.",
  dur_en="about 100 to 110 days", dur_ta="சுமார் 100 முதல் 110 நாட்கள்", dur_tl="sumaar 100 la irundhu 110 naal",
  pest_en="leaf miner and tikka leaf spot", pest_ta="இலைச்சுருட்டுப் புழு மற்றும் டிக்கா இலைப்புள்ளி நோய்", pest_tl="leaf miner, tikka ilai pulli noi"),
 "cotton": dict(
  en="cotton", ta="பருத்தி", tl="paruthi",
  season_en="Cotton is sown in August–September (winter irrigated) and February–March (summer irrigated).",
  season_ta="பருத்தி ஆகஸ்ட்–செப்டம்பர் (குளிர்கால இறவை) மற்றும் பிப்ரவரி–மார்ச் (கோடை இறவை) மாதங்களில் விதைக்கப்படுகிறது.",
  season_tl="Paruthi August–September (winter iravai), February–March (summer iravai) la vidhaikalaam.",
  dur_en="150 to 180 days", dur_ta="150 முதல் 180 நாட்கள்", dur_tl="150 la irundhu 180 naal",
  pest_en="pink bollworm and whitefly", pest_ta="இளஞ்சிவப்பு காய்ப்புழு மற்றும் வெள்ளை ஈ", pest_tl="pink bollworm, vellai ee"),
 "blackgram": dict(
  en="black gram", ta="உளுந்து", tl="ulundhu",
  season_en="Black gram is sown in June–July and September–October, and as a rice-fallow crop in January in the delta.",
  season_ta="உளுந்து ஜூன்–ஜூலை, செப்டம்பர்–அக்டோபர் மாதங்களிலும், டெல்டாவில் ஜனவரியில் நெல் தரிசு பயிராகவும் விதைக்கப்படுகிறது.",
  season_tl="Ulundhu June–July, September–October la vidhaikalaam; delta la January la nel tharisu payira podalaam.",
  dur_en="65 to 75 days", dur_ta="65 முதல் 75 நாட்கள்", dur_tl="65 la irundhu 75 naal",
  pest_en="yellow mosaic disease spread by whitefly", pest_ta="வெள்ளை ஈ மூலம் பரவும் மஞ்சள் தேமல் நோய்", pest_tl="vellai ee moolama paravum manjal themal noi"),
 "maize": dict(
  en="maize", ta="மக்காச்சோளம்", tl="makkacholam",
  season_en="Maize is sown in June–July, September–October and January–February.",
  season_ta="மக்காச்சோளம் ஜூன்–ஜூலை, செப்டம்பர்–அக்டோபர், ஜனவரி–பிப்ரவரி மாதங்களில் விதைக்கப்படுகிறது.",
  season_tl="Makkacholam June–July, September–October, January–February la vidhaikalaam.",
  dur_en="95 to 110 days", dur_ta="95 முதல் 110 நாட்கள்", dur_tl="95 la irundhu 110 naal",
  pest_en="fall armyworm", pest_ta="படைப்புழு", pest_tl="fall armyworm (padai puzhu)"),
 "turmeric": dict(
  en="turmeric", ta="மஞ்சள்", tl="manjal",
  season_en="Turmeric is planted in May–June.",
  season_ta="மஞ்சள் மே–ஜூன் மாதங்களில் நடவு செய்யப்படுகிறது.",
  season_tl="Manjal May–June la nadavu pannalaam.",
  dur_en="7 to 9 months", dur_ta="7 முதல் 9 மாதங்கள்", dur_tl="7 la irundhu 9 maasam",
  pest_en="shoot borer and rhizome rot", pest_ta="தண்டு துளைப்பான் மற்றும் கிழங்கு அழுகல் நோய்", pest_tl="shoot borer, kizhangu azhugal noi"),
 "tomato": dict(
  en="tomato", ta="தக்காளி", tl="thakkali",
  season_en="Tomato can be transplanted in June–July, November–December and January–February.",
  season_ta="தக்காளி ஜூன்–ஜூலை, நவம்பர்–டிசம்பர், ஜனவரி–பிப்ரவரி மாதங்களில் நடவு செய்யலாம்.",
  season_tl="Thakkali June–July, November–December, January–February la nadavu pannalaam.",
  dur_en="about 60–75 days from transplanting to first harvest", dur_ta="நடவு செய்த சுமார் 60–75 நாட்களில் முதல் அறுவடை", dur_tl="nadavu panna 60–75 naal la first aruvadai",
  pest_en="fruit borer and leaf curl virus", pest_ta="காய்ப்புழு மற்றும் இலைச்சுருள் நோய்", pest_tl="kaai puzhu, ilai surul noi"),
 "brinjal": dict(
  en="brinjal", ta="கத்தரி", tl="kathiri",
  season_en="Brinjal can be transplanted in December–January and May–June.",
  season_ta="கத்தரி டிசம்பர்–ஜனவரி மற்றும் மே–ஜூன் மாதங்களில் நடவு செய்யலாம்.",
  season_tl="Kathiri December–January, May–June la nadavu pannalaam.",
  dur_en="about 55–65 days from transplanting to first harvest", dur_ta="நடவு செய்த சுமார் 55–65 நாட்களில் முதல் அறுவடை", dur_tl="nadavu panna 55–65 naal la first aruvadai",
  pest_en="shoot and fruit borer", pest_ta="தண்டு மற்றும் காய் துளைப்பான்", pest_tl="thandu, kaai thulaippan"),
 "chilli": dict(
  en="chilli", ta="மிளகாய்", tl="milagai",
  season_en="Chilli can be transplanted in January–February, June–July and September–October.",
  season_ta="மிளகாய் ஜனவரி–பிப்ரவரி, ஜூன்–ஜூலை, செப்டம்பர்–அக்டோபர் மாதங்களில் நடவு செய்யலாம்.",
  season_tl="Milagai January–February, June–July, September–October la nadavu pannalaam.",
  dur_en="about 75 days from transplanting to the first green chilli harvest", dur_ta="நடவு செய்த சுமார் 75 நாட்களில் பச்சை மிளகாய் அறுவடை தொடங்கும்", dur_tl="nadavu panna 75 naal la pachai milagai aruvadai aarambikkum",
  pest_en="thrips and mites", pest_ta="இலைப்பேன் மற்றும் சிலந்திப்பூச்சி", pest_tl="thrips (ilai pen), silandhi poochi"),
}

def cname(c, lang):
    return c["en"] if lang == "en" else c["ta"] if lang == "ta" else c["tl"]

# ---------------------------------------------------------------- chat intents
# Each: q = {lang: [templates]}, a = {lang: template}, crop = uses {crop}
CHAT_INTENTS = {
 "sowing_season": dict(crop=True,
  q=dict(en=["When should I sow {crop}?", "What is the best season to plant {crop} in Tamil Nadu?", "Which month is good for {crop} cultivation?", "{crop} sowing time?", "When can I start {crop} farming?", "Best time for {crop} planting in {district}?"],
         ta=["{crop} எப்போது விதைக்க வேண்டும்?", "{crop} பயிரிட சிறந்த பருவம் எது?", "{crop} நடவுக்கு எந்த மாதம் நல்லது?", "{district} பகுதியில் {crop} எப்போது நடலாம்?", "{crop} சாகுபடி எப்போது தொடங்கலாம்?"],
         tanglish=["{crop} eppo vidhaikanum?", "{crop} poda best season edhu?", "{crop} nadavu ku endha maasam nalladhu?", "{district} la {crop} eppo podalaam?", "{crop} saagupadi eppo start pannalaam?", "{crop} poda sariyana time sollunga"]),
  a=dict(en="{season_en} Exact timing depends on your variety, water availability and district, so confirm with your block agriculture office or KVK.",
         ta="{season_ta} ரகம், நீர் இருப்பு மற்றும் மாவட்டத்தைப் பொறுத்து நேரம் மாறும்; உங்கள் வட்டார வேளாண் அலுவலகம் அல்லது வேளாண் அறிவியல் நிலையத்தில் உறுதி செய்யுங்கள்.",
         tanglish="{season_tl} Ragam, thanni vasadhi, district poruthu time maarum; unga block agri office illa KVK la confirm pannunga.")),
 "harvest_time": dict(crop=True,
  q=dict(en=["How many days does {crop} take to harvest?", "What is the duration of {crop}?", "When can I harvest my {crop}?", "{crop} crop duration?", "How long does {crop} take to grow?"],
         ta=["{crop} அறுவடைக்கு எத்தனை நாட்கள் ஆகும்?", "{crop} பயிரின் வயது என்ன?", "{crop} எப்போது அறுவடை செய்யலாம்?", "{crop} வளர எவ்வளவு காலம் ஆகும்?"],
         tanglish=["{crop} aruvadaiku evlo naal aagum?", "{crop} duration evlo?", "{crop} eppo aruvadai pannalaam?", "{crop} ku evlo naal venum?", "{crop} valara evlo time aagum?"]),
  a=dict(en="{Crop} usually takes {dur_en}. It varies with variety, season and field conditions.",
         ta="{crop} பொதுவாக {dur_ta} ஆகும். ரகம், பருவம் மற்றும் வயல் நிலையைப் பொறுத்து மாறலாம்.",
         tanglish="{crop} ku podhuva {dur_tl} aagum. Ragam, season, vayal nilai poruthu maarum.")),
 "pest_control": dict(crop=True,
  q=dict(en=["How to control pests in {crop}?", "Insects are attacking my {crop}, what should I do?", "{crop} pest problem", "Which pests affect {crop}?", "My {crop} field has a worm attack"],
         ta=["{crop} பயிரில் பூச்சி தாக்குதலை எப்படி கட்டுப்படுத்துவது?", "என் {crop} வயலில் புழு அதிகமாக உள்ளது, என்ன செய்வது?", "{crop} பயிரைத் தாக்கும் பூச்சிகள் எவை?", "{crop} பூச்சி பிரச்சனை"],
         tanglish=["{crop} la poochi attack, enna pannanum?", "en {crop} vayal la puzhu adhigama iruku", "{crop} ku poochi control epdi?", "{crop} la endha poochi varum?", "{crop} poochi problem sir"]),
  a=dict(en="Common problems in {crop} include {pest_en}. Start with integrated pest management: inspect the field weekly, use pheromone and yellow sticky traps, remove affected parts and use neem-based sprays early. If damage keeps increasing, ask your agriculture officer or KVK for the right pesticide and dose, and always follow the label.",
         ta="{crop} பயிரில் பொதுவாக {pest_ta} தாக்கும். ஒருங்கிணைந்த பூச்சி மேலாண்மையைப் பின்பற்றுங்கள்: வாரம் ஒருமுறை வயலைப் பார்வையிடுங்கள், இனக்கவர்ச்சிப் பொறி மற்றும் மஞ்சள் ஒட்டுப் பொறிகளை வையுங்கள், பாதிக்கப்பட்ட பகுதிகளை அகற்றுங்கள், ஆரம்பத்திலேயே வேப்பம் சார்ந்த மருந்து தெளியுங்கள். சேதம் அதிகரித்தால் சரியான மருந்து மற்றும் அளவுக்கு வேளாண் அலுவலர் அல்லது வேளாண் அறிவியல் நிலையத்தை அணுகுங்கள்.",
         tanglish="{crop} la podhuva {pest_tl} varum. IPM follow pannunga: vaaram oru thadava vayal-a paarunga, pheromone trap, yellow sticky trap vainga, affected part-a remove pannunga, aarambathulaye neem spray adinga. Damage adhigama aana sariyana marundhu, alavu ku agri officer illa KVK kitta kelunga.")),
 "disease_help": dict(crop=True,
  q=dict(en=["My {crop} leaves are turning yellow", "There are spots on my {crop} leaves", "How do I identify {crop} disease?", "My {crop} plants are wilting, why?"],
         ta=["என் {crop} இலைகள் மஞ்சளாக மாறுகின்றன", "{crop} இலைகளில் புள்ளிகள் உள்ளன", "{crop} நோயை எப்படி கண்டறிவது?", "{crop} செடிகள் வாடுகின்றன, ஏன்?"],
         tanglish=["en {crop} ilai manjala maarudhu", "{crop} ilai la pulli iruku", "{crop} noi epdi kandupudikiradhu?", "{crop} sedi vaadudhu, yen?", "{crop} ku noi vandhuruchu pola"]),
  a=dict(en="Yellowing, spots or wilting in {crop} can come from disease, nutrient deficiency or water stress. Send a clear photo of the affected leaf using the attach button and I will analyse it. Meanwhile, remove badly affected leaves and avoid over-watering.",
         ta="{crop} பயிரில் இலை மஞ்சளாதல், புள்ளிகள் அல்லது வாடல் நோய், சத்துக் குறைபாடு அல்லது நீர் அழுத்தத்தால் வரலாம். பாதிக்கப்பட்ட இலையின் தெளிவான புகைப்படத்தை இணைப்பு பொத்தான் மூலம் அனுப்புங்கள், நான் ஆய்வு செய்கிறேன். அதுவரை அதிகம் பாதிக்கப்பட்ட இலைகளை அகற்றுங்கள், அதிக நீர் பாய்ச்ச வேண்டாம்.",
         tanglish="{crop} la ilai manjal aagradhu, pulli, vaadal ellam noi, sathu kuraivu illa thanni stress naala varalaam. Affected ilai oda clear photo-va attach button la anupunga, naan analyse panren. Adhuvarai romba affect aana ilaigala remove pannunga, adhigama thanni paaichadheenga.")),
 "fertilizer_advice": dict(crop=True,
  q=dict(en=["What fertilizer should I use for {crop}?", "How much urea for {crop}?", "Best manure for {crop}?", "{crop} fertilizer schedule"],
         ta=["{crop} பயிருக்கு எந்த உரம் போட வேண்டும்?", "{crop} பயிருக்கு யூரியா எவ்வளவு போடலாம்?", "{crop} பயிருக்கு சிறந்த எரு எது?", "{crop} உர அட்டவணை சொல்லுங்கள்"],
         tanglish=["{crop} ku endha uram podanum?", "{crop} ku urea evlo podalaam?", "{crop} ku best eru edhu?", "{crop} uram schedule sollunga"]),
  a=dict(en="Fertilizer for {crop} should be based on a soil test. Apply well-decomposed farmyard manure or compost before planting, and split nitrogen into 2–3 doses instead of applying it all at once. Get a Soil Health Card from the agriculture office for exact NPK recommendations for your field.",
         ta="{crop} பயிருக்கான உரம் மண் பரிசோதனை அடிப்படையில் இருக்க வேண்டும். நடவுக்கு முன் நன்கு மக்கிய தொழுவுரம் அல்லது மட்கு உரம் இடுங்கள்; தழைச்சத்தை ஒரே முறையில் இல்லாமல் 2–3 முறையாகப் பிரித்து இடுங்கள். உங்கள் நிலத்திற்கான சரியான NPK அளவுக்கு வேளாண் அலுவலகத்தில் மண் வள அட்டை பெறுங்கள்.",
         tanglish="{crop} ku uram soil test adippadaila podanum. Nadavu ku munnadi nalla makkina thozhu uram illa compost podunga; nitrogen-a orey thadava podama 2–3 thadava pirichu podunga. Unga nilathuku correct NPK alavu ku agri office la Soil Health Card vaangunga.")),
 "irrigation": dict(crop=True,
  q=dict(en=["How often should I water {crop}?", "Irrigation tips for {crop}", "Is drip irrigation good for {crop}?", "What is the water requirement of {crop}?"],
         ta=["{crop} பயிருக்கு எத்தனை நாளுக்கு ஒருமுறை தண்ணீர் பாய்ச்ச வேண்டும்?", "{crop} பாசன முறை பற்றி சொல்லுங்கள்", "{crop} பயிருக்கு சொட்டு நீர் பாசனம் நல்லதா?"],
         tanglish=["{crop} ku evlo naal ku oru thadava thanni paaichanum?", "{crop} irrigation tips sollunga", "{crop} ku drip nalladha?", "{crop} ku thanni evlo venum?"]),
  a=dict(en="Irrigation for {crop} depends on soil type, season and crop stage. Water at critical stages like flowering and grain/fruit formation matters most. Where suitable, drip or sprinkler irrigation saves water, and Tamil Nadu gives subsidy for micro irrigation. Ask me about the micro irrigation scheme for details.",
         ta="{crop} பாசனம் மண் வகை, பருவம் மற்றும் பயிர் நிலையைப் பொறுத்தது. பூக்கும் பருவம், மணி/காய் பிடிக்கும் பருவம் போன்ற முக்கிய நிலைகளில் நீர் மிக அவசியம். பொருத்தமான இடங்களில் சொட்டு நீர் அல்லது தெளிப்பு நீர் பாசனம் நீரைச் சேமிக்கும்; தமிழ்நாட்டில் நுண்ணீர் பாசனத்திற்கு மானியம் உண்டு. விவரங்களுக்கு நுண்ணீர் பாசனத் திட்டம் பற்றி என்னிடம் கேளுங்கள்.",
         tanglish="{crop} irrigation mann vagai, season, payir stage poruthu irukum. Poo pookura time, mani/kaai pidikira time la thanni romba mukkiyam. Suitable-a irundha drip illa sprinkler thanni save pannum; Tamil Nadu la micro irrigation ku subsidy iruku. Details ku micro irrigation scheme pathi ennai kelunga.")),
 "seed_selection": dict(crop=True,
  q=dict(en=["Which variety of {crop} is best?", "Where can I buy good {crop} seeds?", "Best {crop} variety for {district}?"],
         ta=["{crop} எந்த ரகம் சிறந்தது?", "நல்ல {crop} விதை எங்கே கிடைக்கும்?", "{district} பகுதிக்கு ஏற்ற {crop} ரகம் எது?"],
         tanglish=["{crop} endha ragam best?", "nalla {crop} vidhai enga kidaikum?", "{district} ku best {crop} ragam edhu?"]),
  a=dict(en="Choose a TNAU-recommended {crop} variety suited to your district and season. Certified seeds are sold at subsidised rates at government Agriculture Extension Centres, and your block agriculture officer can suggest the best variety for your area.",
         ta="உங்கள் மாவட்டம் மற்றும் பருவத்திற்கு ஏற்ற, தமிழ்நாடு வேளாண் பல்கலைக்கழகம் பரிந்துரைக்கும் {crop} ரகத்தைத் தேர்ந்தெடுங்கள். சான்று பெற்ற விதைகள் அரசு வேளாண் விரிவாக்க மையங்களில் மானிய விலையில் கிடைக்கும்; உங்கள் பகுதிக்கு ஏற்ற ரகத்தை வட்டார வேளாண் அலுவலர் பரிந்துரைப்பார்.",
         tanglish="Unga district, season ku yetha TNAU recommend panna {crop} ragatha select pannunga. Certified vidhai govt Agriculture Extension Centre la subsidy vilai la kidaikum; unga area ku best ragam block agri officer solluvaanga.")),
 "market_price": dict(crop=True,
  q=dict(en=["What is today's {crop} price?", "{crop} market rate in {district}?", "Where can I sell {crop} for a good price?"],
         ta=["இன்று {crop} விலை என்ன?", "{district} சந்தையில் {crop} விலை என்ன?", "{crop} எங்கே நல்ல விலைக்கு விற்கலாம்?"],
         tanglish=["inniku {crop} rate enna?", "{district} market la {crop} vilai evlo?", "{crop} enga nalla vilai ku vikkalaam?"]),
  a=dict(en="Prices change daily, so I don't quote fixed rates. Check live prices on the e-NAM portal or the Uzhavan app, or visit your nearest Uzhavar Sandhai or regulated market. Regulated markets give transparent weighing and payment.",
         ta="விலை தினமும் மாறும், அதனால் நான் நிலையான விலை சொல்வதில்லை. e-NAM இணையதளம் அல்லது உழவன் செயலியில் நேரடி விலையைப் பாருங்கள், அல்லது அருகிலுள்ள உழவர் சந்தை அல்லது ஒழுங்குமுறை விற்பனைக் கூடத்திற்குச் செல்லுங்கள். ஒழுங்குமுறை விற்பனைக் கூடங்களில் எடை மற்றும் பணம் வெளிப்படையாக இருக்கும்.",
         tanglish="Vilai dhinamum maarum, adhanaala naan fixed rate solradhu illa. e-NAM portal illa Uzhavan app la live vilai paarunga, illa pakkathula iruka Uzhavar Sandhai illa regulated market ku ponga. Regulated market la edai, panam transparent-a irukum.")),
 "organic_farming": dict(crop=True,
  q=dict(en=["How can I grow {crop} organically?", "Organic methods for {crop}"],
         ta=["{crop} இயற்கை முறையில் எப்படி பயிரிடுவது?", "{crop} இயற்கை விவசாய முறைகள்"],
         tanglish=["{crop} organic-a epdi podradhu?", "{crop} ku iyarkai vivasayam tips"]),
  a=dict(en="For organic {crop}, use compost, vermicompost and green manure, rotate with pulses, apply neem cake and bio-fertilizers like Azospirillum and Phosphobacteria, use Panchagavya as a growth promoter, and manage pests with traps and neem products. Organic cluster and certification support is available under PKVY.",
         ta="இயற்கை முறை {crop} சாகுபடிக்கு மட்கு உரம், மண்புழு உரம், பசுந்தாள் உரம் பயன்படுத்துங்கள்; பயறு வகைகளுடன் பயிர் சுழற்சி செய்யுங்கள்; வேப்பம் புண்ணாக்கு, அசோஸ்பைரில்லம், பாஸ்போபாக்டீரியா போன்ற உயிர் உரங்கள் இடுங்கள்; வளர்ச்சிக்கு பஞ்சகவ்யா தெளியுங்கள்; பூச்சிகளைப் பொறிகள் மற்றும் வேப்பம் பொருட்களால் கட்டுப்படுத்துங்கள். PKVY திட்டத்தில் இயற்கை விவசாயக் குழு மற்றும் சான்றிதழ் உதவி கிடைக்கும்.",
         tanglish="Organic {crop} ku compost, manpuzhu uram, pasundhaal uram use pannunga; payaru vagai kooda crop rotation pannunga; vepam punnaakku, Azospirillum, Phosphobacteria maadhiri bio-fertilizer podunga; valarchi ku Panchagavya spray pannunga; poochi-ku trap, neem products use pannunga. PKVY scheme la organic cluster, certification support kidaikum.")),
 "soil_testing": dict(crop=False,
  q=dict(en=["How do I test my soil?", "Where can I get my soil tested in {district}?", "What is a soil health card?", "How to take a soil sample?"],
         ta=["மண் பரிசோதனை எப்படி செய்வது?", "{district} பகுதியில் மண் பரிசோதனை எங்கே செய்யலாம்?", "மண் வள அட்டை என்றால் என்ன?", "மண் மாதிரி எப்படி எடுப்பது?"],
         tanglish=["soil test epdi pannradhu?", "{district} la mann parisodhanai enga pannalaam?", "soil health card na enna?", "mann sample epdi edukiradhu?"]),
  a=dict(en="Take soil in a V-shaped cut about 15 cm deep from 8–10 spots across the field, mix it, and give about half a kilo to the nearest soil testing laboratory through your agriculture office. You'll get a Soil Health Card showing nutrient status and fertilizer recommendations.",
         ta="வயலின் 8–10 இடங்களில் சுமார் 15 செ.மீ ஆழத்தில் V வடிவில் மண் எடுத்து, நன்கு கலந்து, சுமார் அரை கிலோ மண்ணை வேளாண் அலுவலகம் மூலம் அருகிலுள்ள மண் பரிசோதனை நிலையத்தில் கொடுங்கள். சத்து நிலை மற்றும் உரப் பரிந்துரைகளுடன் மண் வள அட்டை கிடைக்கும்.",
         tanglish="Vayal la 8–10 idathula 15 cm aazhathula V shape la mann eduthu, nalla kalandhu, arai kilo mann-a agri office moolama pakkathu soil testing lab la kudunga. Sathu nilai, uram recommendation oda Soil Health Card kidaikum.")),
 "weather": dict(crop=False,
  q=dict(en=["Will it rain tomorrow in {district}?", "Weather forecast for {district}", "Is it a good time to spray, will it rain?"],
         ta=["நாளை {district} பகுதியில் மழை பெய்யுமா?", "{district} வானிலை எப்படி இருக்கும்?", "மருந்து தெளிக்கலாமா, மழை வருமா?"],
         tanglish=["naalaiku {district} la mazhai varuma?", "{district} weather epdi irukum?", "marundhu adikalaama, mazhai varuma?"]),
  a=dict(en="I can't fetch live weather in this demo. Check the IMD forecast or the weather section of the Uzhavan app for your block. Tip: postpone spraying and fertilizer application if rain is expected within 24 hours.",
         ta="இந்த டெமோவில் நேரடி வானிலையை என்னால் பெற முடியாது. உங்கள் வட்டாரத்திற்கான IMD முன்னறிவிப்பு அல்லது உழவன் செயலியின் வானிலைப் பகுதியைப் பாருங்கள். குறிப்பு: 24 மணி நேரத்தில் மழை எதிர்பார்க்கப்பட்டால் மருந்து தெளிப்பதையும் உரமிடுவதையும் தள்ளிப் போடுங்கள்.",
         tanglish="Indha demo la live weather edukka mudiyaadhu. Unga block ku IMD forecast illa Uzhavan app weather section paarunga. Tip: 24 mani nerathula mazhai varum-na marundhu adikiradhu, uram podradhu rendayum thalli podunga.")),
 "contact_officer": dict(crop=False,
  q=dict(en=["How do I contact the agriculture officer in {district}?", "Who should I contact for farming help in {district}?", "Is there a helpline for farmers?"],
         ta=["{district} வேளாண் அலுவலரை எப்படி தொடர்பு கொள்வது?", "விவசாய உதவிக்கு யாரை அணுகுவது?", "விவசாயிகளுக்கு உதவி எண் உள்ளதா?"],
         tanglish=["{district} agri officer-a epdi contact pannradhu?", "vivasaya help ku yaara paakanum?", "farmers ku helpline number iruka?"]),
  a=dict(en="Visit your block Assistant Director of Agriculture office or the nearest Krishi Vigyan Kendra (KVK). You can also call the Kisan Call Centre at 1800-180-1551 (toll-free) for help in Tamil.",
         ta="உங்கள் வட்டார வேளாண்மை உதவி இயக்குநர் அலுவலகம் அல்லது அருகிலுள்ள வேளாண் அறிவியல் நிலையத்தை (KVK) அணுகுங்கள். கிசான் அழைப்பு மையத்தை 1800-180-1551 (கட்டணமில்லா) எண்ணில் அழைத்து தமிழில் உதவி பெறலாம்.",
         tanglish="Unga block Assistant Director of Agriculture office illa pakkathu KVK ku ponga. Kisan Call Centre 1800-180-1551 (toll-free) ku call panni Tamil la help vaangalaam.")),
 "greeting": dict(crop=False, smalltalk=True,
  q=dict(en=["hi", "hello", "good morning", "hey there", "hello bot"],
         ta=["வணக்கம்", "காலை வணக்கம்", "ஹலோ", "வணக்கம் நண்பா"],
         tanglish=["vanakkam", "hi anna", "hello sir", "vanakkam bot", "hi da"]),
  a=dict(en="Hello! I'm Nilam, your farming assistant 🌾. Ask me about crops, pests, fertilizers or government schemes. You can type, send a voice note, or share a photo of your crop.",
         ta="வணக்கம்! நான் நிலம், உங்கள் விவசாய உதவியாளர் 🌾. பயிர், பூச்சி, உரம் அல்லது அரசு திட்டங்கள் பற்றி கேளுங்கள். தட்டச்சு செய்யலாம், குரல் செய்தி அனுப்பலாம் அல்லது பயிரின் புகைப்படத்தைப் பகிரலாம்.",
         tanglish="Vanakkam! Naan Nilam, unga vivasaya assistant 🌾. Payir, poochi, uram illa govt scheme pathi kelunga. Type pannalaam, voice note anupalaam, illa payir photo share pannalaam.")),
 "thanks": dict(crop=False, smalltalk=True,
  q=dict(en=["thank you", "thanks a lot", "thanks, that helped", "ok thanks"],
         ta=["நன்றி", "மிக்க நன்றி", "ரொம்ப நன்றி, உதவியாக இருந்தது"],
         tanglish=["nandri", "romba nandri", "thanks anna", "super, nandri"]),
  a=dict(en="You're welcome! Wishing you a good harvest. Ask me anytime.",
         ta="மகிழ்ச்சி! நல்ல விளைச்சல் கிடைக்க வாழ்த்துகள். எப்போது வேண்டுமானாலும் கேளுங்கள்.",
         tanglish="Santhosham! Nalla vilaichal kidaikka vaazhthukkal. Eppo venumnaalum kelunga.")),
 "goodbye": dict(crop=False, smalltalk=True,
  q=dict(en=["bye", "see you later", "ok bye"],
         ta=["போய் வருகிறேன்", "சரி, பிறகு பேசலாம்"],
         tanglish=["bye anna", "apram pesalaam", "seri bye"]),
  a=dict(en="Goodbye! Take care of your crops. 🌱",
         ta="சென்று வாருங்கள்! உங்கள் பயிர்களைக் கவனித்துக்கொள்ளுங்கள். 🌱",
         tanglish="Seri, poitu vaanga! Payira nalla paathukonga. 🌱")),
 "bot_identity": dict(crop=False, smalltalk=True,
  q=dict(en=["who are you?", "what can you do?", "are you a human?"],
         ta=["நீங்கள் யார்?", "நீங்கள் என்ன செய்ய முடியும்?", "நீங்கள் மனிதரா?"],
         tanglish=["nee yaaru?", "unnala enna panna mudiyum?", "neenga manushana?"]),
  a=dict(en="I'm Nilam, an AI farming assistant for Tamil Nadu farmers. I'm not a human. I answer questions on crops, pests, fertilizers, irrigation and government schemes in Tamil, English and Tanglish, and I can check crop photos for diseases.",
         ta="நான் நிலம், தமிழ்நாடு விவசாயிகளுக்கான AI விவசாய உதவியாளர். நான் மனிதர் அல்ல. பயிர், பூச்சி, உரம், பாசனம், அரசு திட்டங்கள் பற்றிய கேள்விகளுக்கு தமிழ், ஆங்கிலம், தங்கிலீஷில் பதில் அளிப்பேன்; பயிர் புகைப்படங்களில் நோயையும் கண்டறிவேன்.",
         tanglish="Naan Nilam, Tamil Nadu farmers ku AI vivasaya assistant. Naan manushan illa. Payir, poochi, uram, irrigation, govt scheme pathi Tamil, English, Tanglish la answer panren; payir photo la noi-um check panren.")),
 "image_help": dict(crop=False, smalltalk=True,
  q=dict(en=["how do I send a photo?", "can you check my crop photo?"],
         ta=["புகைப்படம் எப்படி அனுப்புவது?", "என் பயிர் புகைப்படத்தைப் பார்க்க முடியுமா?"],
         tanglish=["photo epdi anupradhu?", "en payir photo paaka mudiyuma?"]),
  a=dict(en="Tap the attach button, pick a clear, close-up photo of one affected leaf in daylight, and send it. I'll tell you the likely disease and what to do.",
         ta="இணைப்பு பொத்தானைத் தட்டி, பகல் வெளிச்சத்தில் பாதிக்கப்பட்ட ஒரு இலையின் தெளிவான அருகாமைப் புகைப்படத்தைத் தேர்ந்தெடுத்து அனுப்புங்கள். சாத்தியமான நோயையும் செய்ய வேண்டியதையும் சொல்கிறேன்.",
         tanglish="Attach button-a thattunga, pagal velichathula affected aana oru ilai-oda clear close-up photo select panni anupunga. Endha noi-nu, enna pannanum-nu solren.")),
 "voice_help": dict(crop=False, smalltalk=True,
  q=dict(en=["can I ask by voice?", "how to send a voice message?"],
         ta=["குரல் மூலம் கேட்கலாமா?", "குரல் செய்தி எப்படி அனுப்புவது?"],
         tanglish=["voice la kekkalaama?", "voice message epdi anupradhu?"]),
  a=dict(en="Yes! Press and hold the mic button, speak your question in Tamil or English, and release to send.",
         ta="ஆம்! மைக் பொத்தானை அழுத்திப் பிடித்து, உங்கள் கேள்வியைத் தமிழிலோ ஆங்கிலத்திலோ பேசி, விட்டுவிட்டால் அனுப்பப்படும்.",
         tanglish="Aamaa! Mic button-a press panni pudichu, unga kelvi-ya Tamil illa English la pesi, vitta anupidum.")),
}

# ---------------------------------------------------------------- augmentation
PREFIX = {
 "en": ["", "Sir, ", "Please tell me, ", "Hi, ", "Can you help? ", "I am a farmer from {district}. "],
 "ta": ["", "ஐயா, ", "வணக்கம், ", "தயவுசெய்து சொல்லுங்கள், ", "நான் {district} விவசாயி. "],
 "tanglish": ["", "sir ", "anna ", "bro ", "vanakkam, ", "naan {district} la irundhu pesuren. "],
}
TL_SPELL = {
 "eppo": ["yeppo", "eppa"], "epdi": ["eppadi", "yepdi"], "enna": ["yenna"], "evlo": ["evvalavu", "evalo"],
 "sollunga": ["solunga", "sollu"], "iruku": ["irukku", "irukudhu"], "pannanum": ["pannanumaa", "panrathu"],
 "nalladhu": ["nalathu"], "kidaikum": ["kedaikum", "kidaikkum"], "podalaam": ["podalama"],
 "thanni": ["thanneer", "tanni"], "vilai": ["velai", "rate"], "mazhai": ["mazha"],
}

def tl_variant(text):
    words = text.split(" ")
    out, changed = [], False
    for w in words:
        core = re.sub(r"[?,.]", "", w.lower())
        if core in TL_SPELL and random.random() < 0.6:
            out.append(w.lower().replace(core, random.choice(TL_SPELL[core]))); changed = True
        else:
            out.append(w)
    return " ".join(out) if changed else None

def en_variant(text):
    t = text.lower().rstrip("?").replace("what is", "whats").replace("how do i", "how to")
    return t if t != text else None

# ---------------------------------------------------------------- build chats
def build_chats():
    rows = []
    for intent, spec in CHAT_INTENTS.items():
        crops = list(CROPS.items()) if spec["crop"] else [(None, None)]
        for lang in LANGS:
            prefixes = [""] if spec.get("smalltalk") else PREFIX[lang]
            for tmpl in spec["q"][lang]:
                for ckey, c in crops:
                    for pre in prefixes:
                        full = pre + tmpl
                        dlist = DISTRICTS if "{district}" in full else [(None, None)]
                        for den, dta in dlist:
                            dname = dta if lang == "ta" else den
                            fmt = dict(district=dname or "")
                            ans_fmt = {}
                            if c:
                                fmt["crop"] = cname(c, lang)
                                ans_fmt = {**c, "crop": cname(c, lang), "Crop": cname(c, lang).capitalize()}
                            q = full.format(**fmt).strip()
                            q = q[0].upper() + q[1:] if lang == "en" and q else q
                            a = spec["a"][lang].format(**ans_fmt) if c else spec["a"][lang]
                            base = dict(lang=lang, intent=intent, crop=ckey or "", district=den or "", answer=a)
                            rows.append({**base, "question": q})
                            v = tl_variant(q) if lang == "tanglish" else en_variant(q) if lang == "en" else None
                            if v:
                                rows.append({**base, "question": v})
    return rows

# ---------------------------------------------------------------- schemes
DOCS = dict(
 en="Aadhaar card, land records (patta/chitta/adangal), bank passbook of an Aadhaar-linked account, mobile number and a passport-size photo.",
 ta="ஆதார் அட்டை, நில ஆவணங்கள் (பட்டா/சிட்டா/அடங்கல்), ஆதாருடன் இணைக்கப்பட்ட வங்கிக் கணக்குப் புத்தகம், மொபைல் எண் மற்றும் பாஸ்போர்ட் அளவு புகைப்படம்.",
 tanglish="Aadhaar card, nila documents (patta/chitta/adangal), Aadhaar link aana bank passbook, mobile number, passport size photo.")

S = lambda **k: k
SCHEMES = [
 S(id="pm_kisan", level="Central", cat="income_support", src="pmkisan.gov.in",
   en="PM-KISAN", ta="பிஎம்-கிசான் (பிரதமரின் விவசாயிகள் கௌரவ நிதி)",
   ben_en="₹6,000 per year in three instalments of ₹2,000, paid directly into the farmer's Aadhaar-linked bank account.",
   ben_ta="ஆண்டுக்கு ₹6,000, மூன்று தவணைகளாக ₹2,000 வீதம், ஆதாருடன் இணைக்கப்பட்ட வங்கிக் கணக்கில் நேரடியாக வரவு வைக்கப்படும்.",
   ben_tl="Varushathuku ₹6,000, moonu thavanaiyaa ₹2,000, Aadhaar link aana bank account ku direct-a varum.",
   eli_en="Farmer families with cultivable land in their name. Income-tax payers, government employees and professionals such as doctors and engineers are excluded. e-KYC is mandatory.",
   eli_ta="தங்கள் பெயரில் சாகுபடி நிலம் உள்ள விவசாயக் குடும்பங்கள். வருமான வரி செலுத்துவோர், அரசு ஊழியர்கள், மருத்துவர்/பொறியாளர் போன்ற தொழில் வல்லுநர்கள் தகுதியற்றவர்கள். e-KYC கட்டாயம்.",
   eli_tl="Unga per la vivasaya nilam iruka farmer family eligible. Income tax kattravanga, govt employees, doctor/engineer maadhiri professionals ku kidaiyaadhu. e-KYC kandippa pannanum.",
   app_en="Register on pmkisan.gov.in (Farmer Corner → New Farmer Registration), at an e-Sevai/CSC centre, or through the agriculture department, then complete e-KYC with OTP or biometrics.",
   app_ta="pmkisan.gov.in இணையதளத்தில் (Farmer Corner → New Farmer Registration), இ-சேவை மையத்தில் அல்லது வேளாண் துறை மூலம் பதிவு செய்து, OTP அல்லது கைரேகை மூலம் e-KYC முடிக்கவும்.",
   app_tl="pmkisan.gov.in la (Farmer Corner → New Farmer Registration), e-Sevai centre la, illa agri department moolama register panni, OTP illa biometric vachu e-KYC mudinga."),
 S(id="pmfby", level="Central", cat="insurance", src="pmfby.gov.in",
   en="PMFBY Crop Insurance", ta="பிரதமரின் பயிர் காப்பீட்டுத் திட்டம் (PMFBY)",
   ben_en="Insurance against crop loss from natural calamities, pests and diseases. Farmer premium is capped at 2% for kharif, 1.5% for rabi and 5% for commercial/horticulture crops; the government pays the rest.",
   ben_ta="இயற்கை பேரிடர், பூச்சி மற்றும் நோயால் ஏற்படும் பயிர் இழப்புக்கு காப்பீடு. விவசாயி பிரீமியம் காரீப் பயிர்களுக்கு 2%, ராபி பயிர்களுக்கு 1.5%, வணிக/தோட்டக்கலைப் பயிர்களுக்கு 5% மட்டுமே; மீதியை அரசு செலுத்தும்.",
   ben_tl="Iyarkai perazhivu, poochi, noi naala varra payir nashtathuku insurance. Farmer premium kharif ku 2%, rabi ku 1.5%, commercial/horticulture ku 5% dhaan; meedhi govt kattum.",
   eli_en="All farmers growing notified crops in notified areas, including tenant farmers and sharecroppers, with or without a crop loan.",
   eli_ta="அறிவிக்கப்பட்ட பகுதிகளில் அறிவிக்கப்பட்ட பயிர்களைச் சாகுபடி செய்யும் அனைத்து விவசாயிகளும், குத்தகை மற்றும் பங்கு விவசாயிகள் உட்பட, கடன் பெற்றவர்களும் பெறாதவர்களும்.",
   eli_tl="Notified area la notified payir podra ella farmers um, kuthagai, pangu vivasayigal um serthu, loan irundhaalum illanaalum.",
   app_en="Enrol before the season's cut-off date through your bank, cooperative society, e-Sevai centre or pmfby.gov.in. Report crop loss within 72 hours through the Crop Insurance app or helpline.",
   app_ta="பருவக் கடைசி தேதிக்குள் வங்கி, கூட்டுறவுச் சங்கம், இ-சேவை மையம் அல்லது pmfby.gov.in மூலம் பதிவு செய்யுங்கள். பயிர் இழப்பை 72 மணி நேரத்திற்குள் Crop Insurance செயலி அல்லது உதவி எண் மூலம் தெரிவியுங்கள்.",
   app_tl="Season last date kulla bank, cooperative society, e-Sevai centre illa pmfby.gov.in la enroll pannunga. Payir nashtam aana 72 mani nerathukulla Crop Insurance app illa helpline la report pannunga.",
   docs_en=" Also a sowing certificate from the VAO.", docs_ta=" மேலும் கிராம நிர்வாக அலுவலரிடமிருந்து விதைப்புச் சான்று.", docs_tl=" VAO kitta irundhu vidhaippu certificate um venum."),
 S(id="kcc", level="Central", cat="credit", src="your bank or cooperative society",
   en="Kisan Credit Card (KCC)", ta="கிசான் கடன் அட்டை (KCC)",
   ben_en="Short-term crop loans at concessional interest. With interest subvention, timely repayment brings the effective rate to about 4% a year on eligible limits. It also covers animal husbandry and fisheries.",
   ben_ta="குறைந்த வட்டியில் குறுகிய காலப் பயிர்க் கடன். வட்டி மானியத்துடன், சரியான நேரத்தில் திருப்பிச் செலுத்தினால் தகுதியான வரம்பில் வட்டி ஆண்டுக்கு சுமார் 4% ஆகும். கால்நடை மற்றும் மீன்வளத்திற்கும் பொருந்தும்.",
   ben_tl="Kammi vatti la short-term payir kadan. Correct time la thiruppi kattina eligible limit ku vatti varushathuku sumaar 4% dhaan. Maadu, meen valarpu kum kidaikum.",
   eli_en="Owner cultivators, tenant farmers, sharecroppers and farmer self-help or joint liability groups.",
   eli_ta="நில உரிமையாளர் விவசாயிகள், குத்தகை விவசாயிகள், பங்கு விவசாயிகள் மற்றும் விவசாயிகளின் சுய உதவி/கூட்டுப் பொறுப்புக் குழுக்கள்.",
   eli_tl="Nila urimaiyaalar, kuthagai vivasayigal, pangu vivasayigal, vivasayigal SHG/group ellarum.",
   app_en="Apply at any commercial bank, regional rural bank or Primary Agricultural Cooperative Credit Society. PM-KISAN beneficiaries can use the simplified one-page KCC form.",
   app_ta="எந்த வணிக வங்கி, கிராம வங்கி அல்லது தொடக்க வேளாண்மைக் கூட்டுறவுக் கடன் சங்கத்திலும் விண்ணப்பிக்கலாம். PM-KISAN பயனாளிகள் எளிய ஒரு பக்க KCC படிவத்தைப் பயன்படுத்தலாம்.",
   app_tl="Endha bank, rural bank, illa cooperative society la yum apply pannalaam. PM-KISAN beneficiaries ku simple one-page KCC form iruku."),
 S(id="soil_health_card", level="Central", cat="soil", src="soilhealth.dac.gov.in",
   en="Soil Health Card", ta="மண் வள அட்டைத் திட்டம்",
   ben_en="Free soil testing and a card showing your field's nutrient status with crop-wise fertilizer recommendations, which helps cut fertilizer cost.",
   ben_ta="இலவச மண் பரிசோதனை; உங்கள் நிலத்தின் சத்து நிலை மற்றும் பயிர்வாரி உரப் பரிந்துரைகளைக் காட்டும் அட்டை. உரச் செலவைக் குறைக்க உதவும்.",
   ben_tl="Free soil test; unga nilathoda sathu nilai, payir vaari uram recommendation kaatura card. Uram selavu kammi aagum.",
   eli_en="All farmers.", eli_ta="அனைத்து விவசாயிகளும்.", eli_tl="Ella vivasayigalum.",
   app_en="Contact your block agriculture office or nearest soil testing laboratory; officials collect samples or you can submit one yourself.",
   app_ta="உங்கள் வட்டார வேளாண் அலுவலகம் அல்லது அருகிலுள்ள மண் பரிசோதனை நிலையத்தை அணுகுங்கள்; அலுவலர்கள் மாதிரி எடுப்பார்கள் அல்லது நீங்களே கொடுக்கலாம்.",
   app_tl="Block agri office illa pakkathu soil testing lab ah contact pannunga; officers sample edupaanga, illa neengale kudukalaam."),
 S(id="pm_kusum", level="Central + State", cat="energy", src="pmkusum.mnre.gov.in and the TN Agricultural Engineering Department",
   en="PM-KUSUM Solar Pump", ta="பிஎம்-குசும் சூரிய மின் பம்ப் திட்டம்",
   ben_en="Subsidy to install standalone solar pumps or solarise existing pumps, reducing diesel and electricity dependence. The subsidy share and farmer contribution are fixed by the state each year.",
   ben_ta="தனி சூரிய மின் பம்புகள் அமைக்க அல்லது உள்ள பம்புகளை சூரிய சக்திக்கு மாற்ற மானியம்; டீசல் மற்றும் மின் சார்பைக் குறைக்கும். மானியப் பங்கும் விவசாயி பங்கும் ஒவ்வொரு ஆண்டும் மாநிலத்தால் நிர்ணயிக்கப்படும்.",
   ben_tl="Solar pump podavo, iruka pump-a solar ku maathavo subsidy; diesel, current selavu kammi aagum. Subsidy share, farmer share ellam state varushaa varusham fix pannum.",
   eli_en="Individual farmers, groups of farmers, FPOs and cooperatives with a water source.",
   eli_ta="நீர் ஆதாரம் உள்ள தனி விவசாயிகள், விவசாயக் குழுக்கள், உழவர் உற்பத்தியாளர் நிறுவனங்கள் மற்றும் கூட்டுறவுகள்.",
   eli_tl="Thanni source iruka thani farmers, farmer groups, FPO, cooperatives.",
   app_en="Apply through the Agricultural Engineering Department office in your district or the state online portal when applications open.",
   app_ta="விண்ணப்பம் திறக்கப்படும்போது உங்கள் மாவட்ட வேளாண் பொறியியல் துறை அலுவலகம் அல்லது மாநில இணையதளம் மூலம் விண்ணப்பிக்கவும்.",
   app_tl="Application open aana appo unga district Agricultural Engineering office illa state online portal la apply pannunga."),
 S(id="pm_kmy", level="Central", cat="pension", src="maandhan.in",
   en="PM Kisan Maandhan Pension", ta="பிரதமரின் கிசான் மான்தன் ஓய்வூதியத் திட்டம்",
   ben_en="A pension of ₹3,000 per month after age 60. The farmer pays a small monthly contribution (₹55–₹200 depending on joining age) and the Central Government adds an equal amount.",
   ben_ta="60 வயதுக்குப் பிறகு மாதம் ₹3,000 ஓய்வூதியம். சேரும் வயதைப் பொறுத்து விவசாயி மாதம் ₹55–₹200 செலுத்துவார்; அதே அளவு தொகையை மத்திய அரசு செலுத்தும்.",
   ben_tl="60 vayasuku apram maasam ₹3,000 pension. Serum vayasa poruthu farmer maasam ₹55–₹200 kattanum; adhe alavu central govt um kattum.",
   eli_en="Small and marginal farmers aged 18 to 40 with up to 2 hectares of cultivable land.",
   eli_ta="18 முதல் 40 வயதுக்குட்பட்ட, 2 ஹெக்டேர் வரை சாகுபடி நிலம் உள்ள சிறு மற்றும் குறு விவசாயிகள்.",
   eli_tl="18 la irundhu 40 vayasu, 2 hectare varai nilam iruka chinna, kuru vivasayigal.",
   app_en="Enrol at a Common Service Centre (CSC) with Aadhaar and bank passbook; monthly contributions are auto-debited.",
   app_ta="ஆதார் மற்றும் வங்கிப் புத்தகத்துடன் பொது சேவை மையத்தில் (CSC) பதிவு செய்யுங்கள்; மாதப் பங்களிப்பு தானாகக் கழிக்கப்படும்.",
   app_tl="Aadhaar, bank passbook eduthuttu CSC centre la enroll pannunga; maasa contribution automatic-a cut aagum."),
 S(id="enam", level="Central", cat="market", src="enam.gov.in",
   en="e-NAM", ta="இ-நாம் (தேசிய மின்னணு வேளாண் சந்தை)",
   ben_en="An online national market where you can sell produce through linked regulated markets with transparent bidding and payment directly to your bank account.",
   ben_ta="இணைக்கப்பட்ட ஒழுங்குமுறை விற்பனைக் கூடங்கள் மூலம் வெளிப்படையான ஏலத்தில் விளைபொருட்களை விற்று, பணத்தை நேரடியாக வங்கிக் கணக்கில் பெறும் ஆன்லைன் தேசியச் சந்தை.",
   ben_tl="Link aana regulated market moolama transparent auction la vilaiporul vithu, panam direct-a bank ku vaangura online national market.",
   eli_en="Farmers, farmer producer organisations and traders registered at e-NAM linked markets.",
   eli_ta="இ-நாம் இணைக்கப்பட்ட சந்தைகளில் பதிவு செய்த விவசாயிகள், உழவர் உற்பத்தியாளர் நிறுவனங்கள் மற்றும் வியாபாரிகள்.",
   eli_tl="e-NAM link market la register panna farmers, FPO, traders.",
   app_en="Register on enam.gov.in, the e-NAM mobile app, or at your nearest e-NAM linked regulated market.",
   app_ta="enam.gov.in, இ-நாம் செயலி அல்லது அருகிலுள்ள இ-நாம் இணைக்கப்பட்ட ஒழுங்குமுறை விற்பனைக் கூடத்தில் பதிவு செய்யுங்கள்.",
   app_tl="enam.gov.in, e-NAM app, illa pakkathu e-NAM regulated market la register pannunga."),
 S(id="pkvy", level="Central", cat="organic", src="your block agriculture office",
   en="PKVY Organic Farming", ta="பரம்பராகத் க்ரிஷி விகாஸ் யோஜனா (இயற்கை விவசாயம்)",
   ben_en="Support for organic farming through farmer clusters, including assistance for organic inputs, training and PGS organic certification.",
   ben_ta="விவசாயக் குழுக்கள் மூலம் இயற்கை விவசாயத்திற்கு ஆதரவு; இயற்கை இடுபொருட்கள், பயிற்சி மற்றும் PGS இயற்கைச் சான்றிதழுக்கு உதவி.",
   ben_tl="Farmer cluster moolama organic farming ku support; organic inputs, training, PGS organic certificate ku help.",
   eli_en="Farmers who form or join a cluster for organic cultivation.",
   eli_ta="இயற்கை சாகுபடிக்கான குழுவை அமைக்கும் அல்லது அதில் சேரும் விவசாயிகள்.",
   eli_tl="Organic cluster start panra illa join panra vivasayigal.",
   app_en="Contact your block agriculture office to join an organic cluster.",
   app_ta="இயற்கை விவசாயக் குழுவில் சேர உங்கள் வட்டார வேளாண் அலுவலகத்தை அணுகுங்கள்.",
   app_tl="Organic cluster la sera unga block agri office ah contact pannunga."),
 S(id="farm_mechanisation", level="Central + State", cat="machinery", src="agrimachinery.nic.in and the TN Agricultural Engineering Department",
   en="Farm Mechanisation Subsidy (SMAM)", ta="வேளாண் இயந்திரமயமாக்கல் மானியம் (SMAM)",
   ben_en="Subsidy on machinery such as power tillers, rotavators and sprayers, plus support for custom hiring centres. Small, marginal, women and SC/ST farmers get a higher subsidy share.",
   ben_ta="பவர் டில்லர், ரோட்டவேட்டர், தெளிப்பான் போன்ற இயந்திரங்களுக்கு மானியம் மற்றும் வாடகை மையங்களுக்கு ஆதரவு. சிறு, குறு, பெண் மற்றும் ஆதிதிராவிடர்/பழங்குடியின விவசாயிகளுக்கு அதிக மானியம்.",
   ben_tl="Power tiller, rotavator, sprayer maadhiri machine ku subsidy, custom hiring centre ku support. Chinna, kuru, pen, SC/ST vivasayigalukku adhiga subsidy.",
   eli_en="All farmers, with priority for small/marginal, women and SC/ST farmers.",
   eli_ta="அனைத்து விவசாயிகளும்; சிறு/குறு, பெண் மற்றும் ஆதிதிராவிடர்/பழங்குடியின விவசாயிகளுக்கு முன்னுரிமை.",
   eli_tl="Ella farmers um; chinna/kuru, pen, SC/ST farmers ku priority.",
   app_en="Apply through the Agricultural Engineering Department or the agrimachinery.nic.in portal when applications open.",
   app_ta="விண்ணப்பம் திறக்கப்படும்போது வேளாண் பொறியியல் துறை அல்லது agrimachinery.nic.in இணையதளம் மூலம் விண்ணப்பிக்கவும்.",
   app_tl="Application open aana appo Agricultural Engineering Department illa agrimachinery.nic.in la apply pannunga."),
 S(id="aif", level="Central", cat="infrastructure", src="agriinfra.dac.gov.in",
   en="Agriculture Infrastructure Fund", ta="வேளாண் உள்கட்டமைப்பு நிதி",
   ben_en="Loans for post-harvest infrastructure such as warehouses, cold storage and primary processing units, with 3% interest subvention on loans up to ₹2 crore and a credit guarantee.",
   ben_ta="கிடங்கு, குளிர்பதனக் கிடங்கு, முதன்மைப் பதப்படுத்தும் அலகுகள் போன்ற அறுவடைக்குப் பிந்தைய உள்கட்டமைப்புக்கு கடன்; ₹2 கோடி வரையிலான கடனுக்கு 3% வட்டி மானியம் மற்றும் கடன் உத்தரவாதம்.",
   ben_tl="Godown, cold storage, processing unit maadhiri aruvadaiku apram thevaiyaana infrastructure ku loan; ₹2 crore varai loan ku 3% vatti subsidy, credit guarantee um iruku.",
   eli_en="Farmers, FPOs, primary agricultural cooperative societies, agri-entrepreneurs and start-ups.",
   eli_ta="விவசாயிகள், உழவர் உற்பத்தியாளர் நிறுவனங்கள், தொடக்க வேளாண் கூட்டுறவுச் சங்கங்கள், வேளாண் தொழில்முனைவோர் மற்றும் ஸ்டார்ட்அப்கள்.",
   eli_tl="Farmers, FPO, cooperative society, agri entrepreneurs, start-ups.",
   app_en="Apply online at agriinfra.dac.gov.in and choose a participating bank.",
   app_ta="agriinfra.dac.gov.in இணையதளத்தில் விண்ணப்பித்து, பங்கேற்கும் வங்கியைத் தேர்ந்தெடுக்கவும்.",
   app_tl="agriinfra.dac.gov.in la online apply panni, participating bank select pannunga."),
 S(id="micro_irrigation", level="Central + State", cat="irrigation", src="tnhorticulture.tn.gov.in (TNHORTNET) or your block agriculture/horticulture office",
   en="Micro Irrigation Subsidy (PMKSY)", ta="நுண்ணீர் பாசன மானியம் (PMKSY)",
   ben_en="Subsidy for drip and sprinkler irrigation. In Tamil Nadu, small and marginal farmers can get up to 100% subsidy and other farmers up to 75%, within unit cost limits.",
   ben_ta="சொட்டு நீர் மற்றும் தெளிப்பு நீர் பாசனத்திற்கு மானியம். தமிழ்நாட்டில் அலகு செலவு வரம்பிற்குள் சிறு, குறு விவசாயிகளுக்கு 100% வரையும் மற்ற விவசாயிகளுக்கு 75% வரையும் மானியம்.",
   ben_tl="Drip, sprinkler irrigation ku subsidy. Tamil Nadu la unit cost limit kulla chinna, kuru vivasayigalukku 100% varai, matha farmers ku 75% varai subsidy.",
   eli_en="Farmers with their own water source and land records; a small/marginal farmer certificate is needed for the 100% subsidy.",
   eli_ta="சொந்த நீர் ஆதாரம் மற்றும் நில ஆவணங்கள் உள்ள விவசாயிகள்; 100% மானியத்திற்கு சிறு/குறு விவசாயி சான்று தேவை.",
   eli_tl="Sondha thanni source, nila documents iruka farmers; 100% subsidy ku chinna/kuru vivasayi certificate venum.",
   app_en="Apply at your block horticulture or agriculture office, or online through TNHORTNET.",
   app_ta="உங்கள் வட்டார தோட்டக்கலை அல்லது வேளாண் அலுவலகத்தில், அல்லது TNHORTNET இணையதளம் மூலம் விண்ணப்பிக்கவும்.",
   app_tl="Unga block horticulture illa agri office la, illa TNHORTNET online la apply pannunga.",
   docs_en=" Also a small/marginal farmer certificate if applicable.", docs_ta=" பொருந்தினால் சிறு/குறு விவசாயி சான்றும் தேவை.", docs_tl=" Thevai-na chinna/kuru vivasayi certificate um venum."),
 S(id="uzhavar_sandhai", level="State", cat="market", src="the TN Agricultural Marketing & Agri Business Department",
   en="Uzhavar Sandhai", ta="உழவர் சந்தை",
   ben_en="Tamil Nadu government farmers' markets where farmers sell fruits and vegetables directly to consumers without middlemen, with shop space and weighing facilities provided.",
   ben_ta="இடைத்தரகர் இல்லாமல் விவசாயிகள் காய்கறி, பழங்களை நேரடியாக நுகர்வோருக்கு விற்கும் தமிழ்நாடு அரசின் சந்தைகள்; கடை இடம் மற்றும் எடை வசதிகள் வழங்கப்படும்.",
   ben_tl="Middleman illama vivasayigal kaaikari, pazham direct-a makkalukku vikkura TN govt market; kadai idam, edai vasadhi kudupaanga.",
   eli_en="Farmers who grow vegetables or fruits and hold an Uzhavar Sandhai identity card.",
   eli_ta="காய்கறி அல்லது பழம் பயிரிடும், உழவர் சந்தை அடையாள அட்டை வைத்துள்ள விவசாயிகள்.",
   eli_tl="Kaaikari illa pazham podra, Uzhavar Sandhai ID card vachirukka vivasayigal.",
   app_en="Contact the Uzhavar Sandhai officer or the Agricultural Marketing department in your district to get a farmer identity card.",
   app_ta="விவசாயி அடையாள அட்டை பெற உழவர் சந்தை அலுவலர் அல்லது மாவட்ட வேளாண் விற்பனைத் துறையை அணுகுங்கள்.",
   app_tl="Farmer ID card vaanga Uzhavar Sandhai officer illa district Agricultural Marketing department ah contact pannunga."),
 S(id="kuruvai_package", level="State", cat="paddy", src="your block agriculture office or the Uzhavan app",
   en="Kuruvai Special Package", ta="குறுவை சிறப்புத் தொகுப்புத் திட்டம்",
   ben_en="A special support package for Kuruvai paddy cultivation, providing inputs such as fertilizers and seeds. In 2026–27 it was extended beyond the Cauvery delta to non-delta paddy farmers. Components are announced each year.",
   ben_ta="குறுவை நெல் சாகுபடிக்கு உரம், விதை போன்ற இடுபொருட்களை வழங்கும் சிறப்பு உதவித் தொகுப்பு. 2026–27ல் காவிரி டெல்டாவைத் தாண்டி டெல்டா அல்லாத நெல் விவசாயிகளுக்கும் விரிவாக்கப்பட்டது. கூறுகள் ஒவ்வொரு ஆண்டும் அறிவிக்கப்படும்.",
   ben_tl="Kuruvai nel saagupadi ku uram, vidhai maadhiri inputs kudukura special package. 2026–27 la Cauvery delta thaandi non-delta nel farmers kum extend pannirukaanga. Enna kidaikum-nu varushaa varusham announce pannuvaanga.",
   eli_en="Paddy farmers cultivating the Kuruvai crop in the areas notified for that year.",
   eli_ta="அந்த ஆண்டு அறிவிக்கப்பட்ட பகுதிகளில் குறுவை நெல் சாகுபடி செய்யும் விவசாயிகள்.",
   eli_tl="Andha varusham notify panna area la Kuruvai nel podra vivasayigal.",
   app_en="Register through your block agriculture office or the Uzhavan app once the package is announced.",
   app_ta="தொகுப்பு அறிவிக்கப்பட்டதும் வட்டார வேளாண் அலுவலகம் அல்லது உழவன் செயலி மூலம் பதிவு செய்யுங்கள்.",
   app_tl="Package announce aanadhum block agri office illa Uzhavan app la register pannunga."),
 S(id="free_power", level="State", cat="energy", src="your local TNPDCL (formerly TANGEDCO) section office",
   en="Free Electricity for Agriculture", ta="விவசாயத்திற்கு இலவச மின்சாரம்",
   ben_en="Free electricity for agricultural pump sets through agricultural service connections from Tamil Nadu's power distribution company (TNPDCL, formerly TANGEDCO).",
   ben_ta="தமிழ்நாடு மின் பகிர்மானக் கழகத்தின் (TNPDCL, முன்பு TANGEDCO) விவசாய மின் இணைப்புகள் மூலம் பம்ப்செட்டுகளுக்கு இலவச மின்சாரம்.",
   ben_tl="TNPDCL (munnadi TANGEDCO) agricultural connection moolama pumpset ku free current.",
   eli_en="Farmers with an agricultural service connection for pump sets.",
   eli_ta="பம்ப்செட்டுக்கு விவசாய மின் இணைப்பு உள்ள விவசாயிகள்.",
   eli_tl="Pumpset ku agricultural current connection iruka farmers.",
   app_en="Apply for a new agricultural service connection at your local electricity section office; connections are given by registration seniority and priority schemes.",
   app_ta="உள்ளூர் மின் பிரிவு அலுவலகத்தில் புதிய விவசாய மின் இணைப்புக்கு விண்ணப்பிக்கவும்; பதிவு மூப்பு மற்றும் முன்னுரிமைத் திட்டங்களின்படி இணைப்பு வழங்கப்படும்.",
   app_tl="Local current office (section office) la pudhu agricultural connection ku apply pannunga; registration seniority, priority scheme padi connection kudupaanga."),
 S(id="paddy_procurement", level="State", cat="paddy", src="tncsc.tn.gov.in or your nearest Direct Purchase Centre",
   en="Paddy Procurement (Direct Purchase Centres)", ta="நெல் கொள்முதல் (நேரடி நெல் கொள்முதல் நிலையங்கள்)",
   ben_en="The TN Civil Supplies Corporation buys paddy at Direct Purchase Centres at the Minimum Support Price plus a state incentive (for KMS 2025–26: ₹1,560/tonne for Grade A and ₹1,310/tonne for common varieties), paid directly to your bank.",
   ben_ta="தமிழ்நாடு நுகர்பொருள் வாணிபக் கழகம் நேரடி கொள்முதல் நிலையங்களில் குறைந்தபட்ச ஆதரவு விலையுடன் மாநில ஊக்கத்தொகையும் சேர்த்து நெல் வாங்குகிறது (KMS 2025–26: சன்ன ரகத்திற்கு டன்னுக்கு ₹1,560, பொது ரகத்திற்கு ₹1,310); பணம் நேரடியாக வங்கிக்கு வரும்.",
   ben_tl="TNCSC Direct Purchase Centre la MSP kooda state incentive um serthu nel vaangum (KMS 2025–26: Grade A ku tonne ku ₹1,560, common ragam ku ₹1,310); panam direct-a bank ku varum.",
   eli_en="Paddy farmers registered with their land and crop details.",
   eli_ta="நிலம் மற்றும் பயிர் விவரங்களுடன் பதிவு செய்த நெல் விவசாயிகள்.",
   eli_tl="Nilam, payir details oda register panna nel vivasayigal.",
   app_en="Register at your nearest Direct Purchase Centre (online registration is also available) with VAO certificate and bank details, then bring your paddy on the allotted date.",
   app_ta="கிராம நிர்வாக அலுவலர் சான்று மற்றும் வங்கி விவரங்களுடன் அருகிலுள்ள நேரடி கொள்முதல் நிலையத்தில் பதிவு செய்யுங்கள் (ஆன்லைன் பதிவும் உண்டு); ஒதுக்கப்பட்ட நாளில் நெல்லைக் கொண்டு வாருங்கள்.",
   app_tl="VAO certificate, bank details oda pakkathu Direct Purchase Centre la register pannunga (online um pannalaam); kudutha date la nel kondu vaanga."),
 S(id="coop_crop_loan", level="State", cat="credit", src="your village Primary Agricultural Cooperative Credit Society",
   en="Cooperative Crop Loan", ta="கூட்டுறவுப் பயிர்க் கடன்",
   ben_en="Short-term crop loans through Primary Agricultural Cooperative Credit Societies; the state plans about ₹17,000 crore in crop loans for 2026–27. Ask your society about interest benefits for timely repayment.",
   ben_ta="தொடக்க வேளாண்மைக் கூட்டுறவுக் கடன் சங்கங்கள் மூலம் குறுகிய காலப் பயிர்க் கடன்; 2026–27ல் சுமார் ₹17,000 கோடி பயிர்க் கடன் வழங்க மாநில அரசு திட்டமிட்டுள்ளது. சரியான நேரத்தில் திருப்பிச் செலுத்தினால் கிடைக்கும் வட்டிச் சலுகை பற்றி உங்கள் சங்கத்தில் கேளுங்கள்.",
   ben_tl="Cooperative society moolama short-term payir kadan; 2026–27 la sumaar ₹17,000 crore payir kadan kudukka state plan panniruku. Correct time la kattina kidaikura vatti salugai pathi unga society la kelunga.",
   eli_en="Farmer members of the local cooperative society with land records.",
   eli_ta="நில ஆவணங்களுடன் உள்ளூர் கூட்டுறவுச் சங்கத்தில் உறுப்பினராக உள்ள விவசாயிகள்.",
   eli_tl="Nila documents oda local cooperative society la member-a iruka farmers.",
   app_en="Become a member of your village cooperative credit society and apply with land records and Aadhaar.",
   app_ta="உங்கள் கிராமக் கூட்டுறவுக் கடன் சங்கத்தில் உறுப்பினராகி, நில ஆவணங்கள் மற்றும் ஆதாருடன் விண்ணப்பிக்கவும்.",
   app_tl="Unga village cooperative society la member aagi, nila documents, Aadhaar oda apply pannunga."),
 S(id="certified_seeds", level="State", cat="seeds", src="your block Agriculture Extension Centre",
   en="Certified Seed Subsidy", ta="சான்று பெற்ற விதை மானியம்",
   ben_en="Certified seeds of paddy, pulses, millets and oilseeds at subsidised rates through Agriculture Extension Centres. The state is continuing the paddy seed subsidy from its own funds in 2026–27.",
   ben_ta="வேளாண் விரிவாக்க மையங்கள் மூலம் நெல், பயறு, சிறுதானியம், எண்ணெய்வித்துப் பயிர்களின் சான்று பெற்ற விதைகள் மானிய விலையில். 2026–27ல் நெல் விதை மானியத்தை மாநில அரசு தன் சொந்த நிதியில் தொடர்கிறது.",
   ben_tl="Agriculture Extension Centre la nel, payaru, siru dhaanyam, ennai vithu certified vidhai subsidy vilai la. 2026–27 la nel vidhai subsidy-a state thanoda sondha fund la continue panudhu.",
   eli_en="All farmers.", eli_ta="அனைத்து விவசாயிகளும்.", eli_tl="Ella vivasayigalum.",
   app_en="Buy from your block Agriculture Extension Centre with Aadhaar and farmer details.",
   app_ta="ஆதார் மற்றும் விவசாயி விவரங்களுடன் வட்டார வேளாண் விரிவாக்க மையத்தில் வாங்கலாம்.",
   app_tl="Aadhaar, farmer details oda block Agriculture Extension Centre la vaangalaam."),
]

SCHEME_Q = {
 "overview": dict(en=["What is {s}?", "Tell me about {s}", "{s} scheme details", "Explain the {s} scheme"],
                  ta=["{s} என்றால் என்ன?", "{s} பற்றி சொல்லுங்கள்", "{s} விவரங்கள்", "{s} பற்றி விளக்குங்கள்"],
                  tanglish=["{s} na enna?", "{s} pathi sollunga", "{s} scheme details venum", "{s} pathi explain pannunga"]),
 "benefit": dict(en=["What benefit do I get from {s}?", "How much money is given under {s}?", "{s} benefits"],
                 ta=["{s} மூலம் என்ன பலன் கிடைக்கும்?", "{s} திட்டத்தில் எவ்வளவு தொகை கிடைக்கும்?", "{s} நன்மைகள் என்ன?"],
                 tanglish=["{s} la enna benefit kidaikum?", "{s} la evlo panam kidaikum?", "{s} benefits enna?"]),
 "eligibility": dict(en=["Who is eligible for {s}?", "Am I eligible for {s}?", "{s} eligibility criteria"],
                     ta=["{s} திட்டத்திற்கு யார் தகுதியானவர்கள்?", "நான் {s} திட்டத்திற்கு தகுதியானவனா?", "{s} தகுதி விதிமுறைகள்"],
                     tanglish=["{s} ku yaar eligible?", "naan {s} ku eligible-a?", "{s} eligibility enna?"]),
 "how_to_apply": dict(en=["How do I apply for {s}?", "Where can I register for {s}?", "{s} application process"],
                      ta=["{s} திட்டத்திற்கு எப்படி விண்ணப்பிப்பது?", "{s} பதிவு எங்கே செய்யலாம்?", "{s} விண்ணப்ப முறை"],
                      tanglish=["{s} ku epdi apply pannradhu?", "{s} register enga pannalaam?", "{s} apply process sollunga"]),
 "documents": dict(en=["What documents are needed for {s}?", "{s} required documents"],
                   ta=["{s} திட்டத்திற்கு என்ன ஆவணங்கள் தேவை?", "{s} தேவையான ஆவணங்கள்"],
                   tanglish=["{s} ku enna documents venum?", "{s} documents list sollunga"]),
 "contact": dict(en=["Where can I get help with {s}?", "{s} official website", "{s} helpline"],
                 ta=["{s} பற்றி உதவி எங்கே கிடைக்கும்?", "{s} அதிகாரப்பூர்வ இணையதளம்", "{s} உதவி எண்"],
                 tanglish=["{s} pathi help enga kidaikum?", "{s} official website enna?", "{s} helpline number"]),
}
SCHEME_PREFIX = {
 "en": ["", "I am a small farmer from {district}. ", "Sir, ", "Please explain: "],
 "ta": ["", "நான் {district} சிறு விவசாயி. ", "ஐயா, "],
 "tanglish": ["", "naan {district} la chinna vivasayi. ", "sir ", "anna "],
}
CAT_TOPIC = {
 "income_support": ("income support", "வருமான உதவி", "income support"),
 "insurance": ("crop insurance", "பயிர் காப்பீடு", "payir insurance"),
 "credit": ("farm loans", "விவசாயக் கடன்", "vivasaya loan"),
 "soil": ("soil testing", "மண் பரிசோதனை", "soil test"),
 "energy": ("electricity and solar pumps", "மின்சாரம் மற்றும் சூரிய பம்ப்", "current, solar pump"),
 "pension": ("farmer pension", "விவசாயி ஓய்வூதியம்", "farmer pension"),
 "market": ("selling my produce", "விளைபொருள் விற்பனை", "vilaiporul vikka"),
 "organic": ("organic farming", "இயற்கை விவசாயம்", "organic vivasayam"),
 "machinery": ("farm machinery", "வேளாண் இயந்திரங்கள்", "vivasaya machine"),
 "infrastructure": ("warehouse and cold storage", "கிடங்கு மற்றும் குளிர்பதனக் கிடங்கு", "godown, cold storage"),
 "irrigation": ("drip irrigation", "சொட்டு நீர் பாசனம்", "drip irrigation"),
 "paddy": ("paddy farmers", "நெல் விவசாயிகள்", "nel vivasayigal"),
 "seeds": ("seeds", "விதைகள்", "vidhai"),
}
DISC_Q = dict(en=["Is there any government scheme for {t}?", "Which schemes help with {t}?", "{t} schemes for Tamil Nadu farmers"],
              ta=["{t} தொடர்பாக ஏதேனும் அரசுத் திட்டம் உள்ளதா?", "{t} தொடர்பான திட்டங்கள் எவை?", "தமிழ்நாடு விவசாயிகளுக்கான {t} திட்டங்கள்"],
              tanglish=["{t} ku edhavadhu govt scheme iruka?", "{t} ku endha scheme iruku?", "Tamil Nadu farmers ku {t} scheme sollunga"])
DISC_A = dict(en="Schemes related to {t}: {names}. Ask me about any of them for eligibility and how to apply.",
              ta="{t} தொடர்பான திட்டங்கள்: {names}. தகுதி மற்றும் விண்ணப்ப முறைக்கு இவற்றில் எதைப் பற்றியும் கேளுங்கள்.",
              tanglish="{t} ku irukka schemes: {names}. Eligibility, apply process ku idhula edha pathi venumnaalum kelunga.")

def scheme_answer(sc, aspect, lang):
    k = {"en": "en", "ta": "ta", "tanglish": "tl"}[lang]
    name = sc["ta"] if lang == "ta" else sc["en"]
    if aspect == "overview":
        return f'{name}: {sc["ben_"+k]} {sc["eli_"+k]}'
    if aspect == "benefit":
        return sc["ben_" + k]
    if aspect == "eligibility":
        return sc["eli_" + k]
    if aspect == "how_to_apply":
        return sc["app_" + k]
    if aspect == "documents":
        return DOCS[lang] + sc.get("docs_" + k, "")
    return {"en": f'For {name}, check {sc["src"]} or visit your block agriculture office. Kisan Call Centre: 1800-180-1551 (toll-free).',
            "ta": f'{name} பற்றி அறிய {sc["src"]} பாருங்கள் அல்லது வட்டார வேளாண் அலுவலகத்தை அணுகுங்கள். கிசான் அழைப்பு மையம்: 1800-180-1551 (கட்டணமில்லா).',
            "tanglish": f'{name} pathi theriya {sc["src"]} paarunga illa block agri office ku ponga. Kisan Call Centre: 1800-180-1551 (toll-free).'}[lang]

def build_schemes():
    rows = []
    for sc in SCHEMES:
        for aspect, qs in SCHEME_Q.items():
            for lang in LANGS:
                sname = sc["ta"] if lang == "ta" else sc["en"]
                ans = scheme_answer(sc, aspect, lang)
                for tmpl in qs[lang]:
                    for pre in SCHEME_PREFIX[lang]:
                        dlist = DISTRICTS if "{district}" in pre else [(None, None)]
                        for den, dta in dlist:
                            q = (pre + tmpl).format(s=sname, district=(dta if lang == "ta" else den) or "")
                            base = dict(lang=lang, intent=aspect, scheme_id=sc["id"], scheme_name=sc["en"],
                                        level=sc["level"], category=sc["cat"], district=den or "",
                                        answer=ans, official_source=sc["src"])
                            rows.append({**base, "question": q})
                            if lang == "tanglish":
                                v = tl_variant(q)
                                if v: rows.append({**base, "question": v})
    # discovery questions (which scheme for X?)
    for cat, (ten, tta, ttl) in CAT_TOPIC.items():
        members = [s for s in SCHEMES if s["cat"] == cat or (cat == "paddy" and s["id"] in ("pmfby", "certified_seeds"))]
        for lang in LANGS:
            t = ten if lang == "en" else tta if lang == "ta" else ttl
            names = ", ".join(s["ta"] if lang == "ta" else s["en"] for s in members)
            ans = DISC_A[lang].format(t=t, names=names)
            for tmpl in DISC_Q[lang]:
                for pre in SCHEME_PREFIX[lang]:
                    dlist = DISTRICTS if "{district}" in pre else [(None, None)]
                    for den, dta in dlist:
                        q = (pre + tmpl).format(t=t, district=(dta if lang == "ta" else den) or "")
                        rows.append(dict(lang=lang, intent="scheme_discovery", scheme_id="multiple",
                                         scheme_name="; ".join(s["en"] for s in members), level="Mixed",
                                         category=cat, district=den or "", answer=ans,
                                         official_source="see individual schemes", question=q))
    return rows

# ---------------------------------------------------------------- sampling
def dedup(rows):
    seen, out = set(), []
    for r in rows:
        key = (r["lang"], r["question"].strip().lower())
        if key not in seen:
            seen.add(key); out.append(r)
    return out

def stratified_sample(rows, target):
    """Equal share per language, then equal share per intent inside each language."""
    by_lang = defaultdict(list)
    for r in rows: by_lang[r["lang"]].append(r)
    per_lang = {l: target // 3 + (1 if i < target % 3 else 0) for i, l in enumerate(LANGS)}
    picked = []
    for lang, quota in per_lang.items():
        by_int = defaultdict(list)
        for r in by_lang[lang]: by_int[r["intent"]].append(r)
        for lst in by_int.values(): random.shuffle(lst)
        share = quota // len(by_int)
        chosen, leftover = [], []
        for lst in by_int.values():
            chosen += lst[:share]; leftover += lst[share:]
        random.shuffle(leftover)
        chosen += leftover[: quota - len(chosen)]
        assert len(chosen) == quota, f"not enough rows for {lang}: {len(chosen)}/{quota}"
        picked += chosen
    random.shuffle(picked)
    return picked

def write(path, rows, cols, prefix):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel shows Tamil correctly
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            r = {**r, "id": f"{prefix}{i:05d}", "source": "synthetic_template",
                 "verify_note": "Approximate; verify with official source / agriculture office"}
            w.writerow({c: r.get(c, "") for c in cols})

if __name__ == "__main__":
    chats = stratified_sample(dedup(build_chats()), TARGET)
    write("tn_farmer_chats.csv", chats,
          ["id", "lang", "intent", "crop", "district", "question", "answer", "source", "verify_note"], "CHAT")
    schemes = stratified_sample(dedup(build_schemes()), TARGET)
    write("tn_farmer_schemes.csv", schemes,
          ["id", "lang", "intent", "scheme_id", "scheme_name", "level", "category", "district",
           "question", "answer", "official_source", "source", "verify_note"], "SCH")
    print("done:", len(chats), "chat rows,", len(schemes), "scheme rows")
