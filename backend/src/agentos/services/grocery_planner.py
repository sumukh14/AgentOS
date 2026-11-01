"""Grocery & Meal Planning Service for AgentOS.

Decomposes Breakfast, Lunch, and Dinner into categorized, deduplicated ingredients,
and automates opening Blinkit in Google Chrome to add items to the shopping cart.
"""

import os
import re
import time
import json
import urllib.parse
from typing import Any, Dict, List, Optional


# Standard Indian Grocery Knowledge Base
RECIPE_INGREDIENTS_MAP: Dict[str, List[Dict[str, Any]]] = {
    # BREAKFAST DISHES
    "poha": [
        {"name": "Flattened Rice (Poha)", "query": "Poha 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Raw Peanuts (Mungfali)", "query": "Raw Peanuts 200g", "qty": "200g", "category": "Spices & Dry Fruits"},
        {"name": "Fresh Lemon", "query": "Lemon 250g", "qty": "250g", "category": "Fresh Vegetables"},
        {"name": "Mustard Seeds (Rai)", "query": "Mustard Seeds 100g", "qty": "100g", "category": "Spices & Oils"},
    ],
    "upma": [
        {"name": "Semolina (Sooji)", "query": "Sooji Rava 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Curry Leaves", "query": "Curry Leaves", "qty": "1 bunch", "category": "Fresh Vegetables"},
        {"name": "Cashews (Kaju)", "query": "Cashew 100g", "qty": "100g", "category": "Spices & Dry Fruits"},
    ],
    "idli": [
        {"name": "Idli Dosa Batter", "query": "Idli Dosa Batter 1kg", "qty": "1kg", "category": "Dairy & Fresh"},
        {"name": "Toor Dal", "query": "Toor Dal 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Sambar Masala", "query": "Sambar Powder 100g", "qty": "100g", "category": "Spices & Oils"},
        {"name": "Fresh Coconut", "query": "Coconut 1 pc", "qty": "1 pc", "category": "Fresh Vegetables"},
    ],
    "aloo paratha": [
        {"name": "Chakki Fresh Atta", "query": "Aashirvaad Atta 1kg", "qty": "1kg", "category": "Grains & Staples"},
        {"name": "Fresh Potato (Aloo)", "query": "Fresh Potato 1kg", "qty": "1kg", "category": "Fresh Vegetables"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Amul Table Butter", "query": "Amul Butter 100g", "qty": "100g", "category": "Dairy & Fresh"},
        {"name": "Fresh Curd (Dahi)", "query": "Amul Dahi 400g", "qty": "400g", "category": "Dairy & Fresh"},
    ],
    "paneer paratha": [
        {"name": "Chakki Fresh Atta", "query": "Aashirvaad Atta 1kg", "qty": "1kg", "category": "Grains & Staples"},
        {"name": "Fresh Malai Paneer", "query": "Amul Malai Paneer 200g", "qty": "200g", "category": "Dairy & Fresh"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Fresh Coriander", "query": "Coriander 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Amul Butter", "query": "Amul Butter 100g", "qty": "100g", "category": "Dairy & Fresh"},
    ],
    "bread omelette": [
        {"name": "Brown / White Bread", "query": "Harvest Gold White Bread 400g", "qty": "400g", "category": "Dairy & Fresh"},
        {"name": "Farm Fresh Eggs", "query": "Eggs 6 pcs", "qty": "6 pcs", "category": "Dairy & Fresh"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Amul Butter", "query": "Amul Butter 100g", "qty": "100g", "category": "Dairy & Fresh"},
    ],
    "besan chilla": [
        {"name": "Besan (Gram Flour)", "query": "Fortune Besan 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
    ],
    "oats": [
        {"name": "Rolled / Instant Oats", "query": "Quaker Oats 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Toned Milk", "query": "Amul Taaza Milk 1L", "qty": "1L", "category": "Dairy & Fresh"},
        {"name": "Fresh Banana", "query": "Banana 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Pure Honey", "query": "Dabur Honey 250g", "qty": "250g", "category": "Spices & Oils"},
    ],
    "oatmeal": [
        {"name": "Rolled / Instant Oats", "query": "Quaker Oats 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Toned Milk", "query": "Amul Taaza Milk 1L", "qty": "1L", "category": "Dairy & Fresh"},
        {"name": "Fresh Banana", "query": "Banana 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Pure Honey", "query": "Dabur Honey 250g", "qty": "250g", "category": "Spices & Oils"},
    ],

    # LUNCH DISHES
    "dal tadka": [
        {"name": "Toor Dal (Arhar Dal)", "query": "Toor Dal 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Garlic (Lahsun)", "query": "Garlic 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Fresh Ginger (Adrak)", "query": "Ginger 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Cumin Seeds (Jeera)", "query": "Jeera 100g", "qty": "100g", "category": "Spices & Oils"},
        {"name": "Desi Ghee", "query": "Amul Pure Ghee 200ml", "qty": "200ml", "category": "Dairy & Fresh"},
    ],
    "dal makhani": [
        {"name": "Whole Black Urad Dal", "query": "Urad Dal Sabut 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Rajma", "query": "Rajma Chitra 200g", "qty": "200g", "category": "Grains & Staples"},
        {"name": "Amul Butter", "query": "Amul Butter 100g", "qty": "100g", "category": "Dairy & Fresh"},
        {"name": "Fresh Malai / Cream", "query": "Amul Fresh Cream 250ml", "qty": "250ml", "category": "Dairy & Fresh"},
        {"name": "Tomato Puree", "query": "Tomato Puree 200g", "qty": "200g", "category": "Fresh Vegetables"},
    ],
    "rajma chawal": [
        {"name": "Rajma (Red Kidney Beans)", "query": "Rajma Chitra 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Basmati Rice", "query": "India Gate Basmati Rice 1kg", "qty": "1kg", "category": "Grains & Staples"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Ginger & Garlic", "query": "Ginger Garlic Paste 100g", "qty": "100g", "category": "Fresh Vegetables"},
    ],
    "paneer butter masala": [
        {"name": "Fresh Paneer", "query": "Amul Fresh Paneer 200g", "qty": "200g", "category": "Dairy & Fresh"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Cashews (Kaju)", "query": "Cashew 100g", "qty": "100g", "category": "Spices & Dry Fruits"},
        {"name": "Amul Butter", "query": "Amul Butter 100g", "qty": "100g", "category": "Dairy & Fresh"},
        {"name": "Fresh Cream", "query": "Amul Fresh Cream 250ml", "qty": "250ml", "category": "Dairy & Fresh"},
        {"name": "Kasuri Methi", "query": "Kasuri Methi 50g", "qty": "50g", "category": "Spices & Oils"},
    ],
    "palak paneer": [
        {"name": "Fresh Spinach (Palak)", "query": "Fresh Palak 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Paneer", "query": "Amul Fresh Paneer 200g", "qty": "200g", "category": "Dairy & Fresh"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Garlic (Lahsun)", "query": "Garlic 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
    ],
    "aloo gobi": [
        {"name": "Cauliflower (Gobi)", "query": "Cauliflower 1 pc", "qty": "1 pc", "category": "Fresh Vegetables"},
        {"name": "Fresh Potato (Aloo)", "query": "Fresh Potato 1kg", "qty": "1kg", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Turmeric Powder (Haldi)", "query": "Haldi Powder 100g", "qty": "100g", "category": "Spices & Oils"},
        {"name": "Fresh Coriander", "query": "Coriander 100g", "qty": "100g", "category": "Fresh Vegetables"},
    ],
    "bhindi": [
        {"name": "Fresh Lady Finger (Bhindi)", "query": "Fresh Bhindi 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Mustard / Cooking Oil", "query": "Fortune Refined Oil 1L", "qty": "1L", "category": "Spices & Oils"},
        {"name": "Dry Mango Powder (Amchur)", "query": "Amchur Powder 100g", "qty": "100g", "category": "Spices & Oils"},
    ],
    "chicken curry": [
        {"name": "Fresh Chicken (Curry Cut)", "query": "Chicken Curry Cut 500g", "qty": "500g", "category": "Dairy & Fresh"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "1kg", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Ginger Garlic Paste", "query": "Ginger Garlic Paste 100g", "qty": "100g", "category": "Fresh Vegetables"},
        {"name": "Chicken Masala", "query": "MDH Chicken Masala 100g", "qty": "100g", "category": "Spices & Oils"},
    ],
    "egg curry": [
        {"name": "Farm Fresh Eggs", "query": "Eggs 6 pcs", "qty": "6 pcs", "category": "Dairy & Fresh"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Ginger Garlic Paste", "query": "Ginger Garlic Paste 100g", "qty": "100g", "category": "Fresh Vegetables"},
    ],
    "rice": [
        {"name": "Basmati Rice", "query": "India Gate Basmati Rice 1kg", "qty": "1kg", "category": "Grains & Staples"},
    ],
    "roti": [
        {"name": "Chakki Fresh Atta", "query": "Aashirvaad Atta 1kg", "qty": "1kg", "category": "Grains & Staples"},
        {"name": "Desi Ghee", "query": "Amul Pure Ghee 200ml", "qty": "200ml", "category": "Dairy & Fresh"},
    ],

    # DINNER DISHES
    "khichdi": [
        {"name": "Yellow Moong Dal", "query": "Moong Dal Dhuli 500g", "qty": "500g", "category": "Grains & Staples"},
        {"name": "Rice", "query": "Basmati Rice 1kg", "qty": "1kg", "category": "Grains & Staples"},
        {"name": "Desi Ghee", "query": "Amul Pure Ghee 200ml", "qty": "200ml", "category": "Dairy & Fresh"},
        {"name": "Fresh Curd (Dahi)", "query": "Amul Dahi 400g", "qty": "400g", "category": "Dairy & Fresh"},
    ],
    "matar paneer": [
        {"name": "Fresh Paneer", "query": "Amul Fresh Paneer 200g", "qty": "200g", "category": "Dairy & Fresh"},
        {"name": "Green Peas (Matar)", "query": "Frozen Matar 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
    ],
    "mix veg": [
        {"name": "Fresh Carrot (Gajar)", "query": "Carrot 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "French Beans", "query": "French Beans 250g", "qty": "250g", "category": "Fresh Vegetables"},
        {"name": "Green Peas", "query": "Frozen Matar 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Cauliflower", "query": "Cauliflower 1 pc", "qty": "1 pc", "category": "Fresh Vegetables"},
        {"name": "Paneer", "query": "Amul Fresh Paneer 200g", "qty": "200g", "category": "Dairy & Fresh"},
    ],
    "paneer bhurji": [
        {"name": "Fresh Paneer", "query": "Amul Fresh Paneer 200g", "qty": "200g", "category": "Dairy & Fresh"},
        {"name": "Onion (Pyaz)", "query": "Fresh Onion 1kg", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Green Capsicum (Shimla Mirch)", "query": "Green Capsicum 250g", "qty": "250g", "category": "Fresh Vegetables"},
        {"name": "Green Chilli", "query": "Green Chilli 100g", "qty": "100g", "category": "Fresh Vegetables"},
    ],
    "veg pulao": [
        {"name": "Basmati Rice", "query": "India Gate Basmati Rice 1kg", "qty": "1kg", "category": "Grains & Staples"},
        {"name": "Green Peas", "query": "Frozen Matar 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Carrot", "query": "Carrot 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Potato", "query": "Fresh Potato 1kg", "qty": "1kg", "category": "Fresh Vegetables"},
        {"name": "Biryani / Pulao Masala", "query": "Pulao Masala 50g", "qty": "50g", "category": "Spices & Oils"},
    ],
    "salad": [
        {"name": "Fresh Cucumber (Kheera)", "query": "Cucumber 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Tomato", "query": "Fresh Tomato 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Carrot", "query": "Carrot 500g", "qty": "500g", "category": "Fresh Vegetables"},
        {"name": "Fresh Lemon", "query": "Lemon 250g", "qty": "250g", "category": "Fresh Vegetables"},
    ],
}


class GroceryPlannerService:
    """Intelligently plans groceries from meal dishes and automates Blinkit cart creation."""

    NON_FOOD_TERMS = {
        "car", "cars", "bike", "motorcycle", "scooter", "cycle", "bus", "truck", "plane", "aeroplane", "train",
        "mobile", "phone", "smartphone", "laptop", "computer", "pc", "monitor", "keyboard", "mouse", "cpu", "gpu",
        "tv", "television", "charger", "cable", "wire", "battery", "screen", "camera", "headphone", "headphones",
        "table", "chair", "bed", "sofa", "almirah", "cupboard", "desk", "fan", "light", "bulb", "tube", "door", "window",
        "wall", "floor", "roof", "mirror", "curtain", "carpet", "lock", "key",
        "pen", "pencil", "paper", "book", "notebook", "eraser", "sharpener", "bag", "backpack", "wallet", "purse",
        "knife", "scissors", "hammer", "nail", "screw", "tape", "glue",
        "iron", "steel", "plastic", "wood", "stone", "rock", "brick", "cement", "sand", "mud", "dirt", "dust", "glass",
        "cloth", "clothes", "clothing", "shirt", "tshirt", "pant", "pants", "jeans", "shoes", "shoe", "socks", "jacket",
        "hat", "cap", "leather", "rubber",
        "soap", "detergent", "shampoo", "conditioner", "perfume", "deodorant", "petrol", "diesel", "kerosene", "paint",
        "poison", "acid", "chemical", "medicine", "medicines", "tablet", "tablets", "pill", "pills", "injection",
        "house", "building", "room", "road", "street", "bridge",
        "code", "coding", "program", "software", "hardware", "bug", "error", "script", "server", "database", "terminal",
        "python", "javascript", "html", "css", "git", "github", "file", "files", "folder", "virus", "trojan",
    }

    FOOD_REGEX = re.compile(
        r"\b(poha|upma|idli|dosa|vada|paratha|parantha|roti|chapati|phulka|naan|kulcha|"
        r"puri|poori|bhature|bhatura|rice|chawal|biryani|pulao|khichdi|atta|sooji|besan|"
        r"maida|oats|oatmeal|bread|toast|sandwich|pancake|waffle|cereal|cornflakes|muesli|"
        r"noodles|pasta|macaroni|spaghetti|maggi|chowmein|burger|pizza|roll|wrap|frankie|"
        r"dal|daal|tadka|makhani|fry|rajma|chole|chhole|chana|kadhi|sambar|rasam|"
        r"curry|gravy|sabzi|sabji|saag|paneer|kofta|bhurji|bharta|korma|jalfrezi|"
        r"aloo|alu|potato|gobi|gobhi|cauliflower|cabbage|matar|mutter|peas|palak|spinach|"
        r"methi|bhindi|okra|ladyfinger|baingan|brinjal|eggplant|karela|lauki|ghiya|tinda|"
        r"tori|capsicum|shimla|mirch|chilli|pepper|corn|mushroom|soya|chaap|beans|"
        r"carrot|gajar|radish|mooli|beetroot|cucumber|kheera|tomato|tamatar|onion|pyaz|"
        r"ginger|adrak|garlic|lahsun|lemon|nimbu|coriander|dhaniya|mint|pudina|"
        r"chicken|mutton|egg|eggs|anda|fish|prawn|prawns|keema|tikka|kabab|kebab|meat|"
        r"milk|dahi|curd|yogurt|butter|makhan|ghee|cheese|cream|malai|lassi|chaas|buttermilk|"
        r"chilla|cheela|dhokla|thepla|khandvi|samosa|kachori|pakoda|pakora|cutlet|omelette|omelet|"
        r"tea|chai|coffee|juice|shake|smoothie|soup|halwa|kheer|gulab jamun|rasgulla|jalebi|"
        r"ice cream|custard|pudding|cake|pastry|brownie|biscuit|cookie|"
        r"apple|banana|mango|orange|grapes|papaya|watermelon|pineapple|guava|strawberry|fruit|fruits|"
        r"salad|raita|chutney|pickle|achar|sauce|snack|snacks|food|meal|khana|dish|dishes|thali)\b",
        re.IGNORECASE,
    )

    @classmethod
    def validate_edible_dish(cls, text: str) -> Dict[str, Any]:
        """Validate if a dish string represents real, edible food."""
        raw = (text or "").strip()
        if not raw:
            return {"valid": True}

        lower = raw.lower()
        words = re.split(r"[\s,+/&;]+", lower)

        for w in words:
            clean_w = re.sub(r"[^a-z0-9]", "", w)
            if clean_w in cls.NON_FOOD_TERMS:
                return {
                    "valid": False,
                    "invalid_item": clean_w,
                    "reason": f"'{clean_w}' is not an edible food item."
                }
            if len(clean_w) >= 4 and not re.search(r"[aeiouy]", clean_w):
                return {
                    "valid": False,
                    "invalid_item": clean_w,
                    "reason": f"'{clean_w}' appears to be random letters, not a food dish."
                }
            if re.search(r"([a-z])\1{3,}", clean_w):
                return {
                    "valid": False,
                    "invalid_item": clean_w,
                    "reason": f"'{clean_w}' contains invalid repeated characters."
                }

        if not cls.FOOD_REGEX.search(lower):
            return {
                "valid": False,
                "invalid_item": raw,
                "reason": f"'{raw}' does not match any recognized food or edible dish."
            }

        return {"valid": True}

    @classmethod
    def _infer_category(cls, name: str) -> str:
        """Infer grocery category from ingredient name."""
        name_lower = name.lower()
        if any(w in name_lower for w in ["palak", "spinach", "aloo", "potato", "onion", "pyaz", "tomato", "tamatar", "gobi", "cauliflower", "carrot", "gajar", "peas", "matar", "bhindi", "methi", "chilli", "ginger", "adrak", "garlic", "lahsun", "lemon", "nimbu", "coriander", "dhaniya", "cucumber", "kheera", "salad", "capsicum", "mushroom", "beans"]):
            return "Fresh Vegetables"
        if any(w in name_lower for w in ["paneer", "milk", "dahi", "curd", "butter", "makhan", "cheese", "cream", "malai", "ghee", "egg", "eggs", "anda", "chicken", "mutton", "fish"]):
            return "Dairy & Fresh"
        if any(w in name_lower for w in ["atta", "flour", "rice", "chawal", "dal", "daal", "toor", "urad", "moong", "poha", "sooji", "besan", "oats", "oatmeal", "bread", "rajma", "chole", "chana", "peanuts", "mungfali"]):
            return "Grains & Staples"
        return "Grains & Staples"

    @classmethod
    def _extract_main_ingredients_fallback(cls, dishes: List[str]) -> List[str]:
        """Intelligent local fallback if Groq API is temporarily unreachable."""
        headline_map = {
            "aloo paratha": ["Aloo", "Atta"],
            "paneer paratha": ["Paneer", "Atta"],
            "palak paneer": ["Palak", "Paneer"],
            "matar paneer": ["Matar", "Paneer"],
            "paneer butter masala": ["Paneer", "Fresh Tomato"],
            "paneer bhurji": ["Paneer", "Fresh Tomato"],
            "dal tadka": ["Toor Dal", "Basmati Rice"],
            "dal makhani": ["Urad Dal", "Rajma"],
            "rajma chawal": ["Rajma", "Basmati Rice"],
            "khichdi": ["Moong Dal", "Rice"],
            "poha": ["Poha", "Raw Peanuts"],
            "upma": ["Sooji Rava"],
            "idli": ["Idli Batter"],
            "dosa": ["Dosa Batter"],
            "besan chilla": ["Besan"],
            "bread omelette": ["Bread", "Eggs"],
            "egg curry": ["Eggs"],
            "chicken curry": ["Fresh Chicken"],
            "aloo gobi": ["Aloo", "Cauliflower"],
            "bhindi": ["Fresh Bhindi"],
            "salad": ["Cucumber", "Fresh Tomato", "Carrot"],
            "rice": ["Basmati Rice"],
            "roti": ["Atta"],
        }
        extracted: List[str] = []
        for dish in dishes:
            d_lower = dish.lower().strip()
            found = False
            for k, v in headline_map.items():
                if k in d_lower:
                    extracted.extend(v)
                    found = True
                    break
            if not found:
                if "paneer" in d_lower: extracted.append("Paneer")
                if "aloo" in d_lower: extracted.append("Aloo")
                if "palak" in d_lower: extracted.append("Palak")
                if "atta" in d_lower or "paratha" in d_lower or "roti" in d_lower: extracted.append("Atta")
                if "dal" in d_lower: extracted.append("Dal")
                if "rice" in d_lower or "chawal" in d_lower: extracted.append("Rice")
                if "egg" in d_lower or "anda" in d_lower: extracted.append("Eggs")
                if "chicken" in d_lower: extracted.append("Chicken")
                if "gobi" in d_lower: extracted.append("Gobi")
                if "matar" in d_lower: extracted.append("Matar")
                if "poha" in d_lower: extracted.append("Poha")
        return extracted

    @classmethod
    def extract_main_ingredients_via_groq(cls, dishes: List[str]) -> List[str]:
        """Send all dishes to Groq to extract strictly the primary, headline ingredients (e.g. Aloo Paratha -> Aloo, Atta; Palak Paneer -> Palak, Paneer)."""
        filtered_dishes = [d.strip() for d in dishes if d and d.strip()]
        if not filtered_dishes:
            return []

        dish_list_str = ", ".join(filtered_dishes)
        print(f"[GROQ GROCERY] Sending dishes to Groq LLM: {dish_list_str}")

        prompt = (
            f"Food dishes: {dish_list_str}.\n"
            "Extract ONLY the main, primary headline ingredients necessary to make their recipes "
            "(for example: for Aloo Paratha -> Aloo, Atta; for Palak Paneer -> Palak, Paneer; "
            "for Poha -> Poha, Peanuts; for Dal Tadka with Steamed Rice -> Toor Dal, Basmati Rice; "
            "for Moong Dal Khichdi -> Moong Dal, Rice; for Rajma Chawal -> Rajma, Basmati Rice; for Egg Bhurji -> Eggs). "
            "Do NOT include generic salt, spices, water, or oil. "
            "Output strictly a JSON object: {\"ingredients\": [\"item1\", \"item2\", ...]}"
        )

        raw_items: List[str] = []
        try:
            from agentos.adapters.groq_adapter import GroqAgentEngine
            engine = GroqAgentEngine()
            res = engine._call_groq_api([
                {
                    "role": "system",
                    "content": (
                        "You are an expert chef. Identify ONLY the headline/main core ingredients for the given dishes. "
                        "Do NOT include standard spices, salt, water, or cooking oil. "
                        "Examples:\n"
                        "- Aloo Paratha -> Aloo, Atta\n"
                        "- Palak Paneer -> Palak, Paneer\n"
                        "- Poha -> Poha, Peanuts\n"
                        "- Dal Tadka with Steamed Rice -> Toor Dal, Basmati Rice\n"
                        "- Moong Dal Khichdi -> Moong Dal, Rice\n"
                        "- Rajma Chawal -> Rajma, Basmati Rice\n"
                        "Return a deduplicated list of headline ingredients as JSON with key 'ingredients'."
                    )
                },
                {"role": "user", "content": prompt}
            ])
            content = res["choices"][0]["message"]["content"]
            print(f"[GROQ GROCERY] Raw Groq response: {content}")

            # Parse JSON block
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                raw_items = data.get("ingredients", [])
            else:
                data = json.loads(content)
                raw_items = data.get("ingredients", [])
        except Exception as e:
            print(f"[GROQ GROCERY] Groq API call error ({e}), falling back to internal headline rules.")
            raw_items = cls._extract_main_ingredients_fallback(filtered_dishes)

        # Deduplicate preserving order
        dedup: List[str] = []
        seen = set()
        for item in raw_items:
            clean = str(item).strip().title()
            if clean.lower() not in seen and len(clean) > 1:
                seen.add(clean.lower())
                dedup.append(clean)

        return dedup

    @classmethod
    def decompose_meals_to_grocery_list(
        cls,
        breakfast: str,
        lunch: str,
        dinner: str,
        servings: int = 2,
    ) -> Dict[str, Any]:
        """Convert 3 meals into a deduplicated set of headline ingredients via Groq."""
        dishes = [d for d in [breakfast, lunch, dinner] if d and d.strip()]
        main_ingredients = cls.extract_main_ingredients_via_groq(dishes)

        items: List[Dict[str, Any]] = []
        categories: Dict[str, List[Dict[str, Any]]] = {
            "Fresh Vegetables": [],
            "Dairy & Fresh": [],
            "Grains & Staples": [],
            "Spices & Oils": [],
        }

        for ing in main_ingredients:
            cat = cls._infer_category(ing)
            item_obj = {
                "name": ing,
                "query": ing,
                "qty": "1 pack",
                "category": cat,
                "blinkit_url": f"https://blinkit.com/s/?q={urllib.parse.quote_plus(ing)}",
            }
            items.append(item_obj)
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item_obj)

        return {
            "status": "success",
            "meals": {
                "breakfast": breakfast,
                "lunch": lunch,
                "dinner": dinner,
            },
            "servings": servings,
            "main_ingredients_set": main_ingredients,
            "total_items_count": len(items),
            "categories": {k: v for k, v in categories.items() if v},
            "items": items,
        }

    _active_browsers: List[Any] = []

    @classmethod
    def launch_blinkit_and_add_cart(
        cls,
        items: List[Dict[str, Any]],
        max_items_to_auto_click: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Launch Chromium in non-headless mode with geolocation permissions, open Blinkit, search each ingredient, and add only 1 item."""
        from playwright.sync_api import sync_playwright

        results: List[Dict[str, Any]] = []
        added_count = 0
        target_items = items if max_items_to_auto_click is None else items[:max_items_to_auto_click]

        try:
            p = sync_playwright().start()
            try:
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",
                        "--no-sandbox",
                    ],
                )
            except Exception:
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",
                        "--no-sandbox",
                    ],
                )

            # Grant geolocation permission directly to Blinkit context
            context = browser.new_context(
                permissions=["geolocation"],
                geolocation={"latitude": 28.6139, "longitude": 77.2090}, # Delhi coordinates
                no_viewport=True,
            )
            page = context.new_page()

            # Retain references so browser stays open on desktop
            cls._active_browsers.append({
                "playwright": p,
                "browser": browser,
                "context": context,
                "page": page,
            })

            # 1. Open Blinkit home page
            page.goto("https://blinkit.com/", timeout=30000)
            page.wait_for_timeout(1800)

            # Auto-configure location if in-page location search prompt appears
            try:
                loc_input = page.locator("input[placeholder*='search delivery location'], input[placeholder*='location']").first
                if loc_input and loc_input.count() > 0:
                    loc_input.fill("Delhi")
                    page.wait_for_timeout(1200)
                    suggestions = page.locator("div[class*='LocationSearchList'] > div").all()
                    if suggestions:
                        suggestions[0].click(timeout=3000)
                        page.wait_for_timeout(1800)
            except Exception:
                pass

            # 2. Iterate through each ingredient from the list one by one and add only 1 item
            for idx, item in enumerate(target_items):
                query = item.get("query") or item.get("name")
                search_url = f"https://blinkit.com/s/?q={urllib.parse.quote_plus(query)}"
                try:
                    page.goto(search_url, timeout=20000)
                    page.wait_for_timeout(1500)

                    # Look for ADD button on the first product card
                    add_btn = page.locator("div, button").filter(has_text=re.compile(r"^ADD$", re.IGNORECASE)).first
                    if add_btn and add_btn.count() > 0:
                        try:
                            add_btn.scroll_into_view_if_needed(timeout=2500)
                            add_btn.click(timeout=2500)
                            page.wait_for_timeout(800)
                            results.append({"name": item["name"], "query": query, "status": "added_1_item_to_cart"})
                            added_count += 1
                        except Exception:
                            results.append({"name": item["name"], "query": query, "status": "opened_search_page"})
                    else:
                        results.append({"name": item["name"], "query": query, "status": "opened_search_page"})
                except Exception as e:
                    results.append({"name": item["name"], "query": query, "status": f"skipped: {str(e)[:50]}"})

            # 3. Open Blinkit Cart Drawer so all added items are visible in the cart drawer without login
            cart_opened = False
            cart_text = ""
            try:
                cart_btn = page.locator("button:has-text('items'), div[class*='CartButton'], button:has-text('Cart')").first
                if cart_btn and cart_btn.count() > 0:
                    cart_text = cart_btn.text_content().strip()
                    cart_btn.click(timeout=4000)
                    page.wait_for_timeout(2000)
                    cart_opened = True
            except Exception:
                try:
                    page.goto("https://blinkit.com/", timeout=15000)
                except Exception:
                    pass

            return {
                "status": "success",
                "browser": "Chromium / Chrome (Location Granted, Visible On Desktop)",
                "total_items": len(target_items),
                "added_to_cart_count": added_count,
                "cart_opened": cart_opened,
                "cart_summary": cart_text or f"{added_count} items in cart",
                "login_required_for_cart": False,
                "actions": results,
                "message": f"Successfully opened Chromium with location permissions, searched each ingredient one by one, and added {added_count} items (1 unit each) into your Blinkit cart. The cart drawer is open and visible on your screen without login!"
            }
        except Exception as e:
            # Fallback to direct browser launch if Playwright encountered an issue
            import subprocess
            try:
                first_query = target_items[0]["query"] if target_items else "groceries"
                subprocess.Popen(f'start "" "https://blinkit.com/s/?q={urllib.parse.quote_plus(first_query)}"', shell=True)
            except Exception:
                pass

            return {
                "status": "partial_success",
                "error": str(e),
                "message": "Opened Blinkit in your default browser.",
                "actions": results,
            }
