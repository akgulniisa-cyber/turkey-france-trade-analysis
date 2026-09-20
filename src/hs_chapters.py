"""English names for the 2-digit HS chapters.

The public UN Comtrade preview endpoint returns ``cmdDesc`` as ``null``, so the
product labels have to come from a local reference table. This module holds the
97 chapter codes that appear in the data (HS chapters 01-97, where 77 is
reserved and unused, plus 99 for goods that are not classified elsewhere).

Each chapter is described by:
  * ``short_name`` - a few words, for chart axes and dashboard tables
  * ``full_name``  - the official chapter heading, for tooltips and reports
  * ``section``    - the Roman numeral of the HS section it belongs to
"""

from __future__ import annotations

import pandas as pd

# The 21 HS sections group the chapters into broad industries.
HS_SECTIONS: dict[str, str] = {
    "I": "Live animals and animal products",
    "II": "Vegetable products",
    "III": "Animal and vegetable fats and oils",
    "IV": "Prepared foodstuffs, beverages and tobacco",
    "V": "Mineral products",
    "VI": "Chemical and allied industries",
    "VII": "Plastics and rubber",
    "VIII": "Hides, skins, leather and furs",
    "IX": "Wood, cork and straw",
    "X": "Pulp, paper and printed products",
    "XI": "Textiles and textile articles",
    "XII": "Footwear, headgear and accessories",
    "XIII": "Stone, cement, ceramics and glass",
    "XIV": "Pearls, precious stones and metals",
    "XV": "Base metals and articles of base metal",
    "XVI": "Machinery and electrical equipment",
    "XVII": "Vehicles, aircraft and transport equipment",
    "XVIII": "Instruments, clocks and musical instruments",
    "XIX": "Arms and ammunition",
    "XX": "Miscellaneous manufactured articles",
    "XXI": "Works of art and antiques",
    # Deliberately not "NA": pandas reads that string back as a null value.
    "NC": "Not classified",
}

# code -> (short_name, full_name, section)
HS_CHAPTERS: dict[str, tuple[str, str, str]] = {
    "01": ("Live animals", "Live animals", "I"),
    "02": ("Meat", "Meat and edible meat offal", "I"),
    "03": (
        "Fish and seafood",
        "Fish and crustaceans, molluscs and other aquatic invertebrates",
        "I",
    ),
    "04": (
        "Dairy, eggs and honey",
        "Dairy produce; birds' eggs; natural honey; edible products of animal origin",
        "I",
    ),
    "05": (
        "Other animal products",
        "Products of animal origin, not elsewhere specified or included",
        "I",
    ),
    "06": (
        "Live plants and flowers",
        "Live trees and other plants; bulbs, roots; cut flowers and ornamental foliage",
        "II",
    ),
    "07": (
        "Vegetables",
        "Edible vegetables and certain roots and tubers",
        "II",
    ),
    "08": (
        "Fruit and nuts",
        "Edible fruit and nuts; peel of citrus fruit or melons",
        "II",
    ),
    "09": ("Coffee, tea and spices", "Coffee, tea, mate and spices", "II"),
    "10": ("Cereals", "Cereals", "II"),
    "11": (
        "Milling products",
        "Products of the milling industry; malt; starches; inulin; wheat gluten",
        "II",
    ),
    "12": (
        "Oil seeds and grains",
        "Oil seeds and oleaginous fruits; miscellaneous grains, seeds and fruit; "
        "industrial or medicinal plants; straw and fodder",
        "II",
    ),
    "13": (
        "Gums and resins",
        "Lac; gums, resins and other vegetable saps and extracts",
        "II",
    ),
    "14": (
        "Other vegetable products",
        "Vegetable plaiting materials; vegetable products not elsewhere specified",
        "II",
    ),
    "15": (
        "Fats and oils",
        "Animal or vegetable fats and oils and their cleavage products; "
        "prepared edible fats; animal or vegetable waxes",
        "III",
    ),
    "16": (
        "Prepared meat and fish",
        "Preparations of meat, fish or crustaceans, molluscs or other aquatic invertebrates",
        "IV",
    ),
    "17": ("Sugar and confectionery", "Sugars and sugar confectionery", "IV"),
    "18": ("Cocoa", "Cocoa and cocoa preparations", "IV"),
    "19": (
        "Cereal and bakery preparations",
        "Preparations of cereals, flour, starch or milk; pastrycooks' products",
        "IV",
    ),
    "20": (
        "Prepared vegetables and fruit",
        "Preparations of vegetables, fruit, nuts or other parts of plants",
        "IV",
    ),
    "21": ("Misc. edible preparations", "Miscellaneous edible preparations", "IV"),
    "22": ("Beverages and spirits", "Beverages, spirits and vinegar", "IV"),
    "23": (
        "Food residues and fodder",
        "Residues and waste from the food industries; prepared animal fodder",
        "IV",
    ),
    "24": ("Tobacco", "Tobacco and manufactured tobacco substitutes", "IV"),
    "25": (
        "Salt, stone and cement",
        "Salt; sulphur; earths and stone; plastering materials, lime and cement",
        "V",
    ),
    "26": ("Ores and slag", "Ores, slag and ash", "V"),
    "27": (
        "Mineral fuels and oils",
        "Mineral fuels, mineral oils and products of their distillation; "
        "bituminous substances; mineral waxes",
        "V",
    ),
    "28": (
        "Inorganic chemicals",
        "Inorganic chemicals; organic or inorganic compounds of precious metals, "
        "rare-earth metals, radioactive elements or isotopes",
        "VI",
    ),
    "29": ("Organic chemicals", "Organic chemicals", "VI"),
    "30": ("Pharmaceuticals", "Pharmaceutical products", "VI"),
    "31": ("Fertilisers", "Fertilisers", "VI"),
    "32": (
        "Dyes, paints and inks",
        "Tanning or dyeing extracts; dyes, pigments, paints, varnishes, putty and inks",
        "VI",
    ),
    "33": (
        "Cosmetics and perfumery",
        "Essential oils and resinoids; perfumery, cosmetic or toilet preparations",
        "VI",
    ),
    "34": (
        "Soap and waxes",
        "Soap, organic surface-active agents, washing and lubricating preparations, "
        "waxes, polishing preparations, candles",
        "VI",
    ),
    "35": (
        "Glues and enzymes",
        "Albuminoidal substances; modified starches; glues; enzymes",
        "VI",
    ),
    "36": (
        "Explosives and matches",
        "Explosives; pyrotechnic products; matches; pyrophoric alloys; "
        "certain combustible preparations",
        "VI",
    ),
    "37": ("Photographic goods", "Photographic or cinematographic goods", "VI"),
    "38": ("Misc. chemical products", "Miscellaneous chemical products", "VI"),
    "39": ("Plastics", "Plastics and articles thereof", "VII"),
    "40": ("Rubber", "Rubber and articles thereof", "VII"),
    "41": (
        "Raw hides and leather",
        "Raw hides and skins (other than furskins) and leather",
        "VIII",
    ),
    "42": (
        "Leather goods",
        "Articles of leather; saddlery and harness; travel goods, handbags; "
        "articles of animal gut",
        "VIII",
    ),
    "43": (
        "Furskins",
        "Furskins and artificial fur; manufactures thereof",
        "VIII",
    ),
    "44": ("Wood", "Wood and articles of wood; wood charcoal", "IX"),
    "45": ("Cork", "Cork and articles of cork", "IX"),
    "46": (
        "Basketware",
        "Manufactures of straw, esparto or other plaiting materials; "
        "basketware and wickerwork",
        "IX",
    ),
    "47": (
        "Wood pulp",
        "Pulp of wood or other fibrous cellulosic material; recovered paper or paperboard",
        "X",
    ),
    "48": (
        "Paper and paperboard",
        "Paper and paperboard; articles of paper pulp, of paper or of paperboard",
        "X",
    ),
    "49": (
        "Printed products",
        "Printed books, newspapers, pictures and other products of the printing "
        "industry; manuscripts and typescripts",
        "X",
    ),
    "50": ("Silk", "Silk", "XI"),
    "51": (
        "Wool and animal hair",
        "Wool, fine or coarse animal hair; horsehair yarn and woven fabric",
        "XI",
    ),
    "52": ("Cotton", "Cotton", "XI"),
    "53": (
        "Other vegetable fibres",
        "Other vegetable textile fibres; paper yarn and woven fabrics of paper yarn",
        "XI",
    ),
    "54": (
        "Man-made filaments",
        "Man-made filaments; strip and the like of man-made textile materials",
        "XI",
    ),
    "55": ("Man-made staple fibres", "Man-made staple fibres", "XI"),
    "56": (
        "Nonwovens and cordage",
        "Wadding, felt and nonwovens; special yarns; twine, cordage, ropes and cables",
        "XI",
    ),
    "57": ("Carpets", "Carpets and other textile floor coverings", "XI"),
    "58": (
        "Special woven fabrics",
        "Special woven fabrics; tufted textile fabrics; lace; tapestries; "
        "trimmings; embroidery",
        "XI",
    ),
    "59": (
        "Technical textiles",
        "Impregnated, coated, covered or laminated textile fabrics; "
        "textile articles for industrial use",
        "XI",
    ),
    "60": ("Knitted fabrics", "Knitted or crocheted fabrics", "XI"),
    "61": (
        "Knitted apparel",
        "Articles of apparel and clothing accessories, knitted or crocheted",
        "XI",
    ),
    "62": (
        "Non-knitted apparel",
        "Articles of apparel and clothing accessories, not knitted or crocheted",
        "XI",
    ),
    "63": (
        "Other textile articles",
        "Other made-up textile articles; sets; worn clothing and worn textile "
        "articles; rags",
        "XI",
    ),
    "64": ("Footwear", "Footwear, gaiters and the like; parts of such articles", "XII"),
    "65": ("Headgear", "Headgear and parts thereof", "XII"),
    "66": (
        "Umbrellas and walking sticks",
        "Umbrellas, sun umbrellas, walking sticks, whips, riding crops and parts thereof",
        "XII",
    ),
    "67": (
        "Feathers and artificial flowers",
        "Prepared feathers and down; artificial flowers; articles of human hair",
        "XII",
    ),
    "68": (
        "Stone and cement articles",
        "Articles of stone, plaster, cement, asbestos, mica or similar materials",
        "XIII",
    ),
    "69": ("Ceramics", "Ceramic products", "XIII"),
    "70": ("Glass and glassware", "Glass and glassware", "XIII"),
    "71": (
        "Precious stones and metals",
        "Natural or cultured pearls, precious or semi-precious stones, precious "
        "metals; imitation jewellery; coin",
        "XIV",
    ),
    "72": ("Iron and steel", "Iron and steel", "XV"),
    "73": ("Iron and steel articles", "Articles of iron or steel", "XV"),
    "74": ("Copper", "Copper and articles thereof", "XV"),
    "75": ("Nickel", "Nickel and articles thereof", "XV"),
    "76": ("Aluminium", "Aluminium and articles thereof", "XV"),
    "78": ("Lead", "Lead and articles thereof", "XV"),
    "79": ("Zinc", "Zinc and articles thereof", "XV"),
    "80": ("Tin", "Tin and articles thereof", "XV"),
    "81": (
        "Other base metals",
        "Other base metals; cermets; articles thereof",
        "XV",
    ),
    "82": (
        "Tools and cutlery",
        "Tools, implements, cutlery, spoons and forks, of base metal; parts thereof",
        "XV",
    ),
    "83": (
        "Misc. base metal articles",
        "Miscellaneous articles of base metal",
        "XV",
    ),
    "84": (
        "Machinery",
        "Nuclear reactors, boilers, machinery and mechanical appliances; parts thereof",
        "XVI",
    ),
    "85": (
        "Electrical equipment",
        "Electrical machinery and equipment and parts thereof; sound and television "
        "recorders and reproducers",
        "XVI",
    ),
    "86": (
        "Railway equipment",
        "Railway or tramway locomotives, rolling stock and parts thereof; "
        "track fixtures and signalling equipment",
        "XVII",
    ),
    "87": (
        "Vehicles",
        "Vehicles other than railway or tramway rolling stock, and parts and "
        "accessories thereof",
        "XVII",
    ),
    "88": ("Aircraft and spacecraft", "Aircraft, spacecraft, and parts thereof", "XVII"),
    "89": ("Ships and boats", "Ships, boats and floating structures", "XVII"),
    "90": (
        "Optical and medical instruments",
        "Optical, photographic, cinematographic, measuring, checking, precision, "
        "medical or surgical instruments and apparatus",
        "XVIII",
    ),
    "91": ("Clocks and watches", "Clocks and watches and parts thereof", "XVIII"),
    "92": (
        "Musical instruments",
        "Musical instruments; parts and accessories of such articles",
        "XVIII",
    ),
    "93": ("Arms and ammunition", "Arms and ammunition; parts and accessories thereof", "XIX"),
    "94": (
        "Furniture and lighting",
        "Furniture; bedding, mattresses, cushions; lamps and lighting fittings; "
        "illuminated signs; prefabricated buildings",
        "XX",
    ),
    "95": (
        "Toys and sports equipment",
        "Toys, games and sports requisites; parts and accessories thereof",
        "XX",
    ),
    "96": ("Misc. manufactured articles", "Miscellaneous manufactured articles", "XX"),
    "97": (
        "Works of art and antiques",
        "Works of art, collectors' pieces and antiques",
        "XXI",
    ),
    "99": (
        "Not classified",
        "Commodities not elsewhere specified",
        "NC",
    ),
}

# Chapter 99 is a residual bucket that Comtrade uses for confidential or
# unallocated trade. It is a real part of the totals but it is not a product,
# so the opportunity analysis excludes it.
SPECIAL_CHAPTERS = {"99"}


def chapters_frame() -> pd.DataFrame:
    """Return the chapter reference as a DataFrame, ready to be merged."""
    rows = [
        {
            "hs_code": code,
            "hs_short_name": short,
            "hs_name": full,
            "hs_section": section,
            "hs_section_name": HS_SECTIONS[section],
            "is_special": code in SPECIAL_CHAPTERS,
        }
        for code, (short, full, section) in HS_CHAPTERS.items()
    ]
    return pd.DataFrame(rows).sort_values("hs_code").reset_index(drop=True)
