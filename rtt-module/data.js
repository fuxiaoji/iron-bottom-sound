// 由 export_rtt_data.py 生成，勿手改
"use strict"
var data = {
  meta: {
    "generator": "scripts/export_rtt_data.py",
    "generated_at": "2026-09-11T18:51:40+00:00",
    "counts": {
      "ships": 214,
      "scenarios": 16,
      "templates": 8,
      "gunnery_hit_rows": 20,
      "armour_penetration_rows": 27
    }
  }, hex: {
    "MAX_COLUMNS": 128,
    "MAX_ROWS": 128,
    "direction_delta": {
      "1": [1, -1],
      "2": [1, 0],
      "3": [0, 1],
      "4": [-1, 1],
      "5": [-1, 0],
      "6": [0, -1]
    }
  }, rules: {
    "fireTable": {
      "schema_version": 1,
      "id": "IBS-T-FIRE",
      "source": {
        "document": "player-aid-tables-zh.pdf",
        "pdf_page": 1,
        "status": "verified_source"
      },
      "status": "structured",
      "results": {
        "2": {
          "kind": "special_damage",
          "armour_already_penetrated": true
        },
        "3": {
          "primary": 1,
          "hull": 1
        },
        "4": {
          "extinguish": true,
          "applies_to": "US_only"
        },
        "5-6": {
          "kind": "no_effect"
        },
        "7": {
          "hull": 1
        },
        "8-9": {
          "extinguish": true
        },
        "10": {
          "kind": "no_effect"
        },
        "11": {
          "hull": 1,
          "secondary": 1,
          "speed_loss": 1
        },
        "12": {
          "kind": "special_damage",
          "armour_already_penetrated": true
        }
      },
      "modifiers": {
        "ship_did_not_fire": 1,
        "ignore_results_if_ship_did_not_fire": [7, 12]
      },
      "notes": [
        "离开地图后仍继续火灾判定，除非舰只沉没；离图后的火灾损伤计入分数。"
      ]
    },
    "specialDamage": {
      "schema_version": 1,
      "id": "IBS-T-SPECIAL-DAMAGE",
      "source": {
        "document": "player-aid-tables-zh.pdf",
        "pdf_page": 4,
        "status": "verified_source"
      },
      "status": "structured",
      "notes": [
        "在所有 44–65 结果中均须执行装甲穿透检定。",
        "百分比航速损失按初始最大航速的四分之一或二分之一向下取整。"
      ],
      "displacement_bands": [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I"
      ],
      "direct_results": {
        "11": {
          "fire": 1,
          "narrative": "防空炮弹药起火"
        },
        "12": {
          "fire": 1,
          "narrative": "舰内食堂起火"
        },
        "13": {
          "fire": 1,
          "narrative": "油料起火"
        },
        "14": {
          "fire": 1,
          "narrative": "医护室起火，负伤船员被烧死"
        },
        "15": {
          "fire": 1,
          "narrative": "船员休息室起火"
        },
        "16": {
          "fire": 1,
          "torpedo_launcher_hit": 1
        },
        "21": {
          "hull": 1,
          "speed_loss": 1,
          "torpedo_launcher_hit": 1
        },
        "22": {
          "hull": 1,
          "torpedo_launcher_hit": 1
        },
        "23": {
          "fire": 1,
          "hull": 1,
          "torpedo_launcher_hit": 1
        },
        "24": {
          "rudder_hit": true,
          "armour_check": true,
          "armour_location": "belt",
          "future_turn_limit_degrees": 60
        },
        "25": {
          "rudder_hit": true,
          "armour_check": true,
          "armour_location": "belt",
          "straight_turns": 3
        },
        "26": {
          "rudder_hit": true,
          "circle_turns": 2,
          "fire_control": true
        },
        "31": {
          "bridge_hit": true,
          "bridge_armour_check": true,
          "radar": true,
          "next_turn_straight_at_original_speed": true,
          "captain_killed": true
        },
        "32": {
          "bridge_hit": true,
          "hold_turn_degrees": 60,
          "circle_turns": 2,
          "captain_wounded": true
        },
        "33-36": {
          "fire": 1,
          "hull": 1,
          "ignore_fire_if_no_aircraft": true,
          "fire_control": true
        },
        "41": {
          "fire": 1,
          "hull": 2,
          "ignore_fire_if_no_aircraft": true
        },
        "42": {
          "hull": 2,
          "primary": 2,
          "secondary": 1,
          "radar": true,
          "captain_killed": true
        },
        "43": {
          "sunk": true,
          "armour_check": true,
          "armour_location": "belt"
        },
        "66": {
          "all_guns_disabled_turns": 1,
          "captain_wounded": true
        }
      },
      "results": {
        "44": {
          "A": "1H/-2MF",
          "B": "1H/-2MF",
          "C": "1H/-2MF",
          "D": "1H/-2MF",
          "E": "2H/-2MF",
          "F": "2H/-2MF",
          "G": "2H/-2MF",
          "H": "2H/-2MF",
          "I": "2H/-1MF"
        },
        "45": {
          "A": "1H/-4MF",
          "B": "1H/-4MF",
          "C": "2H/-3MF",
          "D": "2H/-3MF",
          "E": "3H/-3MF",
          "F": "3H/-2MF",
          "G": "2H/-2MF",
          "H": "2H/-2MF",
          "I": "1H/-2MF"
        },
        "46": {
          "A": "1H",
          "B": "2H",
          "C": "2H",
          "D": "2H",
          "E": "2H",
          "F": "2H",
          "G": "2H",
          "H": "2H",
          "I": "2H",
          "additional": "secondary_1"
        },
        "51": {
          "A": "1H",
          "B": "1H",
          "C": "1H",
          "D": "1H",
          "E": "3H",
          "F": "3H",
          "G": "4H",
          "H": "4H",
          "I": "5H",
          "additional": "secondary_1"
        },
        "52": {
          "A": "2H/-1MF",
          "B": "2H/-1MF",
          "C": "3H/-1MF",
          "D": "3H/-1MF",
          "E": "4H/-1MF",
          "F": "4H/-1MF",
          "G": "4H/-1MF",
          "H": "4H/-1MF",
          "I": "5H/-1MF",
          "additional": "primary_1"
        },
        "53": {
          "A": "1H/-2MF",
          "B": "1H/-2MF",
          "C": "2H/-2MF",
          "D": "2H/-2MF",
          "E": "3H/-2MF",
          "F": "3H/-2MF",
          "G": "4H/-2MF",
          "H": "4H/-2MF",
          "I": "4H/-2MF",
          "additional": "primary_1"
        },
        "54": {
          "A": "1H",
          "B": "2H",
          "C": "3H",
          "D": "3H",
          "E": "4H",
          "F": "4H",
          "G": "5H",
          "H": "5H",
          "I": "5H",
          "additional": "primary_1_secondary_1"
        },
        "55": {
          "A": "1H/-5MF",
          "B": "2H/-6MF",
          "C": "3H/-6MF",
          "D": "3H/-4MF",
          "E": "4H/-4MF",
          "F": "4H/-3MF",
          "G": "4H/-3MF",
          "H": "4H/-3MF",
          "I": "4H/-3MF"
        },
        "56": {
          "A": "1H/-11MF",
          "B": "1H/-11MF",
          "C": "2H/-6MF",
          "D": "2H/-6MF",
          "E": "2H/-6MF",
          "F": "2H/-6MF",
          "G": "2H/-6MF",
          "H": "2H/-6MF",
          "I": "2H/-6MF"
        },
        "61": {
          "A": "1H/-3MF",
          "B": "1H/-3MF",
          "C": "2H/-3MF",
          "D": "2H/-3MF",
          "E": "3H/-3MF",
          "F": "3H/-3MF",
          "G": "3H/-3MF",
          "H": "3H/-3MF",
          "I": "3H/-3MF"
        },
        "62": {
          "A": "1H/-50%",
          "B": "1H/-50%",
          "C": "1H/-50%",
          "D": "1H/-50%",
          "E": "1H/-50%",
          "F": "1H/-50%",
          "G": "1H/-50%",
          "H": "1H/-50%",
          "I": "1H/-50%"
        },
        "63": {
          "A": "1H/-100%",
          "B": "1H/-100%",
          "C": "2H/-100%",
          "D": "2H/-100%",
          "E": "3H/-25%",
          "F": "3H/-25%",
          "G": "3H/-25%",
          "H": "3H/-25%",
          "I": "3H/-25%"
        },
        "64": {
          "A": "1H/-25%",
          "B": "1H/-25%",
          "C": "2H/-25%",
          "D": "2H/-25%",
          "E": "3H/-25%",
          "F": "3H/-25%",
          "G": "3H/-25%",
          "H": "3H/-25%",
          "I": "3H/-25%"
        },
        "65": {
          "A": "1H/-50%",
          "B": "1H/-50%",
          "C": "2H/-50%",
          "D": "2H/-50%",
          "E": "2H/-50%",
          "F": "2H/-50%",
          "G": "3H/-50%",
          "H": "2H/-50%",
          "I": "2H/-50%"
        }
      }
    },
    "gunneryHitTable": [
      {
        "firepower_min": 1,
        "firepower_max": 1,
        "11": 1,
        "12": 1,
        "13": 0,
        "14": 0,
        "15": 0,
        "16": 0,
        "21": 0,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 2,
        "firepower_max": 2,
        "11": 2,
        "12": 1,
        "13": 0,
        "14": 0,
        "15": 0,
        "16": 0,
        "21": 0,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 3,
        "firepower_max": 3,
        "11": 2,
        "12": 1,
        "13": 1,
        "14": 1,
        "15": 0,
        "16": 0,
        "21": 0,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 4,
        "firepower_max": 4,
        "11": 2,
        "12": 2,
        "13": 1,
        "14": 1,
        "15": 1,
        "16": 0,
        "21": 0,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 5,
        "firepower_max": 5,
        "11": 2,
        "12": 2,
        "13": 1,
        "14": 1,
        "15": 1,
        "16": 1,
        "21": 0,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 6,
        "firepower_max": 6,
        "11": 2,
        "12": 2,
        "13": 2,
        "14": 1,
        "15": 1,
        "16": 1,
        "21": 0,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 7,
        "firepower_max": 7,
        "11": 2,
        "12": 2,
        "13": 2,
        "14": 2,
        "15": 1,
        "16": 1,
        "21": 1,
        "22": 0,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 8,
        "firepower_max": 8,
        "11": 3,
        "12": 2,
        "13": 2,
        "14": 2,
        "15": 1,
        "16": 1,
        "21": 1,
        "22": 1,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 9,
        "firepower_max": 10,
        "11": 3,
        "12": 3,
        "13": 2,
        "14": 2,
        "15": 2,
        "16": 1,
        "21": 1,
        "22": 1,
        "23": 0,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 11,
        "firepower_max": 13,
        "11": 3,
        "12": 3,
        "13": 2,
        "14": 2,
        "15": 2,
        "16": 2,
        "21": 2,
        "22": 1,
        "23": 1,
        "24": 0,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 14,
        "firepower_max": 17,
        "11": 4,
        "12": 3,
        "13": 3,
        "14": 2,
        "15": 2,
        "16": 2,
        "21": 2,
        "22": 2,
        "23": 1,
        "24": 1,
        "25": 0,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 18,
        "firepower_max": 22,
        "11": 4,
        "12": 3,
        "13": 3,
        "14": 3,
        "15": 3,
        "16": 2,
        "21": 2,
        "22": 2,
        "23": 2,
        "24": 1,
        "25": 1,
        "26": 0,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 23,
        "firepower_max": 26,
        "11": 5,
        "12": 4,
        "13": 3,
        "14": 3,
        "15": 3,
        "16": 3,
        "21": 2,
        "22": 2,
        "23": 2,
        "24": 2,
        "25": 1,
        "26": 1,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 27,
        "firepower_max": 36,
        "11": 5,
        "12": 4,
        "13": 4,
        "14": 3,
        "15": 3,
        "16": 3,
        "21": 3,
        "22": 2,
        "23": 2,
        "24": 2,
        "25": 2,
        "26": 1,
        "31": 0,
        "32_plus": 0
      },
      {
        "firepower_min": 37,
        "firepower_max": 46,
        "11": 5,
        "12": 5,
        "13": 4,
        "14": 4,
        "15": 4,
        "16": 3,
        "21": 3,
        "22": 3,
        "23": 2,
        "24": 2,
        "25": 2,
        "26": 1,
        "31": 1,
        "32_plus": 0
      },
      {
        "firepower_min": 47,
        "firepower_max": 56,
        "11": 5,
        "12": 5,
        "13": 5,
        "14": 4,
        "15": 4,
        "16": 4,
        "21": 3,
        "22": 3,
        "23": 3,
        "24": 3,
        "25": 2,
        "26": 2,
        "31": 1,
        "32_plus": 0
      },
      {
        "firepower_min": 57,
        "firepower_max": 66,
        "11": 6,
        "12": 5,
        "13": 5,
        "14": 5,
        "15": 4,
        "16": 4,
        "21": 4,
        "22": 4,
        "23": 3,
        "24": 3,
        "25": 3,
        "26": 2,
        "31": 1,
        "32_plus": 0
      },
      {
        "firepower_min": 67,
        "firepower_max": 85,
        "11": 6,
        "12": 6,
        "13": 5,
        "14": 5,
        "15": 5,
        "16": 4,
        "21": 4,
        "22": 4,
        "23": 4,
        "24": 4,
        "25": 3,
        "26": 2,
        "31": 2,
        "32_plus": 0
      },
      {
        "firepower_min": 86,
        "firepower_max": 100,
        "11": 7,
        "12": 6,
        "13": 6,
        "14": 6,
        "15": 5,
        "16": 5,
        "21": 4,
        "22": 4,
        "23": 4,
        "24": 4,
        "25": 4,
        "26": 2,
        "31": 2,
        "32_plus": 0
      },
      {
        "firepower_min": 101,
        "firepower_max": 9999,
        "11": 7,
        "12": 7,
        "13": 6,
        "14": 6,
        "15": 5,
        "16": 5,
        "21": 5,
        "22": 5,
        "23": 5,
        "24": 4,
        "25": 4,
        "26": 3,
        "31": 2,
        "32_plus": 0
      }
    ],
    "gunneryResults": {
      "11": "special",
      "12": "special",
      "13": "primary_bow",
      "14": "special",
      "15": {
        "hull": 2,
        "armour_check": true
      },
      "16": "special",
      "21": {
        "hull": 1,
        "speed_loss": 1
      },
      "22": {
        "hull": 1
      },
      "23": {
        "hull": 2,
        "speed_loss": 1
      },
      "24": {
        "hull": 1,
        "armour_check": true
      },
      "25": {
        "hull_by_ship_type": {
          "BB_BC": 3,
          "AV_CA_CL": 2,
          "other": 1
        }
      },
      "26": {
        "hull_by_ship_type": {
          "BB_BC": 2,
          "other": 1
        }
      },
      "31": {
        "secondary": 1,
        "armour_check": true
      },
      "32": "special",
      "33": {
        "primary_stern": 1,
        "fire_check_for_jp_de_4.7_or_5": true
      },
      "34": [
        "special",
        "radar"
      ],
      "35": {
        "primary_mid": 1,
        "armour_check": true
      },
      "36": {
        "primary_bow": 1,
        "armour_check": true
      },
      "41": [
        "fire_control",
        "radar"
      ],
      "42": {
        "secondary": 1
      },
      "43": {
        "secondary": 1,
        "armour_check": true
      },
      "44": "special",
      "45": "special",
      "46": {
        "primary_stern": 1,
        "armour_check": true
      },
      "51": [
        "primary_mid",
        "radar"
      ],
      "52": [
        "secondary",
        "fire_control"
      ],
      "53": {
        "hull": 1,
        "speed_loss": 1
      },
      "54": {
        "hull": 1,
        "armour_check": true
      },
      "55": {
        "hull": 1,
        "fire_check": true
      },
      "56": {
        "primary_bow": 1,
        "armour_check": true
      },
      "61": {
        "primary_stern": 1,
        "armour_check": true
      },
      "62": {
        "secondary": 1,
        "armour_check": true
      },
      "63": {
        "secondary": 1,
        "armour_check": true
      },
      "64": [
        "primary_bow",
        "radar"
      ],
      "65": {
        "hull": 1,
        "armour_check": true
      },
      "66+": "miss"
    },
    "torpedoCollision": {
      "schema_version": 1,
      "id": "IBS-T-THDT",
      "source": {
        "document": "player-aid-tables-zh.pdf",
        "pdf_page": 3,
        "status": "verified_source"
      },
      "columns": [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I"
      ],
      "rows": {
        "2-": [
          "1H/-4MF",
          "1H/-4MF",
          "1H/-3MF",
          "1H/-3MF",
          "1H/-2MF",
          "1H/-2MF",
          "1H/-1MF",
          "1H/-1MF",
          "1H/-1MF"
        ],
        "3": [
          "Miss",
          "Miss",
          "Miss",
          "Miss",
          "Miss",
          "Miss",
          "Miss",
          "Miss",
          "Miss"
        ],
        "4": [
          "1H/-5MF",
          "5H/-11MF",
          "2H/-3MF",
          "1H/-2MF",
          "1H/-1MF",
          "1H/-1MF",
          "1H",
          "1H",
          "1H"
        ],
        "5": [
          "1H/-11MF",
          "2H/-5MF*",
          "3H/-3MF",
          "2H/-3MF",
          "2H/-2MF",
          "2H/-1MF",
          "1H/-1MF",
          "-1MF",
          "1H"
        ],
        "6": [
          "1H/-7MF*",
          "1H/-7MF",
          "4H/-5MF",
          "3H/-2MF",
          "2H/-2MF",
          "2H/-2MF",
          "2H/-1MF",
          "1H/-1MF",
          "1H"
        ],
        "7": [
          "2H/-13MF",
          "3H/-6MF",
          "4H/-6MF",
          "4H/-5MF",
          "4H/-3MF",
          "3H/-1MF",
          "3H/-2MF",
          "3H/-1MF",
          "2H/-1MF"
        ],
        "8": [
          "Sunk",
          "4H/-9MF",
          "5H/-7MF",
          "4H/-5MF",
          "4H/-3MF",
          "3H/-2MF",
          "3H/-2MF",
          "3H/-1MF",
          "2H/-1MF"
        ],
        "9": [
          "Sunk",
          "Sunk",
          "5H/-6MF",
          "5H/-5MF",
          "4H/-2MF",
          "4H/-2MF",
          "3H/-2MF",
          "2H/-2MF",
          "2H/-1MF"
        ],
        "10": [
          "Sunk",
          "Sunk",
          "6H",
          "5H/-6MF",
          "5H/-4MF",
          "4H/-3MF",
          "4H/-3MF",
          "3H/-2MF",
          "3H/-2MF"
        ],
        "11": [
          "Sunk",
          "Sunk",
          "7H",
          "5H/-8MF*",
          "4H/-6MF",
          "4H/-4MF",
          "3H/-4MF",
          "2H/-2MF",
          "2H/-2MF"
        ],
        "12+": [
          "Sunk",
          "Sunk",
          "8H",
          "6H/-10MF",
          "7H/-1MF*",
          "4H/-5MF*",
          "4H/-5MF*",
          "3H/-3MF*",
          "3H/-2MF*"
        ]
      },
      "notes": [
        "H means hull damage; MF means speed loss; starred results also cause fire.",
        "Sum 8 results always cause fire regardless of printed star."
      ]
    },
    "torpedoes": {
      "us-21-mk11-model3-1928": {
        "nation": "US",
        "caliber_in": 21,
        "settings": [
          {
            "speed": [8, 8, 2],
            "range": 10
          },
          {
            "speed": [6, 6, 4],
            "range": 16
          },
          {
            "speed": [5, 5, 4],
            "range": 21
          }
        ],
        "damage_modifier": -2
      },
      "us-21-mk11-model4-1928": {
        "nation": "US",
        "caliber_in": 21,
        "settings": [
          {
            "speed": [8, 8, 2],
            "range": 10
          },
          {
            "speed": [6, 6, 4],
            "range": 16
          },
          {
            "speed": [5, 4, 4],
            "range": 30
          }
        ],
        "damage_modifier": -1
      },
      "us-21-mk15-1942": {
        "nation": "US",
        "caliber_in": 21,
        "settings": [
          {
            "speed": [8, 8, 2],
            "range": 10
          },
          {
            "speed": [6, 6, 4],
            "range": 16
          },
          {
            "speed": [5, 4, 4],
            "range": 25
          }
        ],
        "damage_modifier": 0
      },
      "uk-21-mk7c": {
        "nation": "UK",
        "applies_to": [
          "Australia",
          "New Zealand"
        ],
        "caliber_in": 21,
        "settings": [
          {
            "speed": [6, 6, 5],
            "range": 11
          },
          {
            "speed": [6, 6, 5],
            "range": 17
          },
          {
            "speed": [5, 5, 5],
            "range": 22
          }
        ],
        "damage_modifier": 0
      },
      "uk-21-mk9": {
        "nation": "UK",
        "caliber_in": 21,
        "settings": [
          {
            "speed": [6, 5, 5],
            "range": 18
          },
          {
            "speed": [5, 4, 4],
            "range": 25
          }
        ],
        "damage_modifier": 0
      },
      "jp-21": {
        "nation": "JP",
        "caliber_in": 21,
        "settings": [
          {
            "speed": [8, 8, 2],
            "range": 10
          },
          {
            "speed": [6, 6, 6],
            "range": 18
          }
        ],
        "damage_modifier": -1
      },
      "jp-24-type8": {
        "nation": "JP",
        "caliber_in": 24,
        "settings": [
          {
            "speed": [7, 6, 6],
            "range": 18
          },
          {
            "speed": [6, 5, 5],
            "range": 27
          },
          {
            "speed": [5, 5, 4],
            "range": 36
          }
        ],
        "damage_modifier": 0
      },
      "jp-24-type90": {
        "nation": "JP",
        "caliber_in": 24,
        "settings": [
          {
            "speed": [8, 7, 7],
            "range": 12
          },
          {
            "speed": [7, 7, 7],
            "range": 18
          },
          {
            "speed": [6, 6, 6],
            "range": 27
          }
        ],
        "damage_modifier": 0
      },
      "jp-24-type93": {
        "nation": "JP",
        "caliber_in": 24,
        "settings": [
          {
            "speed": [8, 8, 8],
            "range": 36
          },
          {
            "speed": [7, 7, 7],
            "range": 58
          },
          {
            "speed": [6, 6, 6],
            "range": 71
          }
        ],
        "damage_modifier": 1
      },
      "de-nl-21": {
        "nation": "DE_NL",
        "caliber_in": 21,
        "settings": [
          {
            "speed": [8, 8, 2],
            "range": 10
          },
          {
            "speed": [7, 7, 7],
            "range": 14
          },
          {
            "speed": [5, 5, 5],
            "range": 25
          }
        ],
        "damage_modifier": 0
      }
    },
    "torpedoLaunchDirections": {
      "rule_id": "IBS-R-08.2",
      "source": {
        "document": "iron-bottom-sound-iv-rules-zh.pdf",
        "pdf_page": 11,
        "printed_section": "8.2.3 b"
      },
      "angles": [
        "A",
        "B",
        "X",
        "Y"
      ],
      "relative_heading": {
        "port": {
          "A": -1,
          "B": -1,
          "X": -2,
          "Y": -2
        },
        "starboard": {
          "A": 1,
          "B": 1,
          "X": 2,
          "Y": 2
        }
      },
      "launch_anchor": {
        "A": 0,
        "B": -1,
        "X": 1,
        "Y": 0
      }
    },
    "modifiers": {
      "schema_version": 1,
      "source": {
        "document": "player-aid-tables-zh.pdf",
        "pdf_pages": [2, 3, 4],
        "status": "verified_source"
      },
      "range_modifier": {
        "gunnery": [
          {
            "min": 1,
            "max": 1,
            "value": -24
          },
          {
            "min": 2,
            "max": 2,
            "value": -15
          },
          {
            "min": 3,
            "max": 5,
            "value": -12
          },
          {
            "min": 6,
            "max": 9,
            "value": -6
          },
          {
            "min": 10,
            "max": 15,
            "value": 0
          },
          {
            "min": 16,
            "max": 20,
            "value": 2
          },
          {
            "min": 21,
            "max": 999,
            "value": 4
          }
        ],
        "torpedo": [
          {
            "min": 1,
            "max": 2,
            "value": 5
          },
          {
            "min": 3,
            "max": 4,
            "value": 3
          },
          {
            "min": 5,
            "max": 6,
            "value": 1
          },
          {
            "min": 7,
            "max": 10,
            "value": 0
          },
          {
            "min": 11,
            "max": 15,
            "value": 0,
            "non_japanese_additional": -1
          },
          {
            "min": 16,
            "max": 999,
            "value": -1
          }
        ]
      },
      "target_speed_modifier": {
        "gunnery": {
          "0": -18,
          "1": -9,
          "2-3": -4,
          "4+": 0
        },
        "torpedo": {
          "0": 4,
          "1": 4,
          "2": 2,
          "3": 1,
          "4+": 0
        }
      },
      "longitudinal_modifier": [
        {
          "min": 1,
          "max": 1,
          "value": -8
        },
        {
          "min": 2,
          "max": 2,
          "value": -8
        },
        {
          "min": 3,
          "max": 5,
          "value": -8
        },
        {
          "min": 6,
          "max": 9,
          "value": -6
        },
        {
          "min": 10,
          "max": 15,
          "value": -4
        },
        {
          "min": 16,
          "max": 20,
          "value": -1
        },
        {
          "min": 21,
          "max": 999,
          "value": 0
        }
      ],
      "target_aspect_modifier": {
        "gunnery_bow_stern": -6,
        "torpedo_bow_stern": -8
      },
      "other": {
        "target_on_fire": -2,
        "each_additional_attacker": 1,
        "each_additional_target": 6,
        "mfc_destroyed": 3,
        "searchlight_target": -3,
        "searchlight_user": -3
      },
      "optional": {
        "star_shell_or_radar_illumination": 3,
        "target_searchlit": -3,
        "searchlight_user": -3,
        "through_smoke": 6
      },
      "gunnery_caliber_target_modifier": {
        "columns": [
          "BB_BC",
          "CA",
          "CL_AV",
          "DD_APD"
        ],
        "rows": {
          "11-18": [0, -3, -3, 3],
          "7.5-8": [6, 0, 0, 0],
          "5.25-6.1": [12, 0, 0, 0],
          "3-5.1": [18, 6, 6, 0]
        }
      },
      "torpedo_hit": {
        "broadside": {
          "2-10": 0,
          "11-12": 1,
          "13+": 2
        },
        "bow_stern": {
          "2-12": 0,
          "13+": 1
        }
      },
      "collision_modifier": {
        "columns": [
          "wreck",
          "DD_APD",
          "CA_CL_AV",
          "BB_BC"
        ],
        "rows": {
          "BB_BC": [-4, -5, -4, -3],
          "CA_CL_AV": [-4, -4, -3, -2],
          "DD_APD": [-4, -3, -2, -1]
        },
        "both_moved_2mf_or_less": -1
      }
    },
    "armourPenetration": [
      {
        "gun_id": "us-16-45",
        "nation": "US",
        "caliber_in": 16,
        "period": "post_1942",
        "1-2": 25,
        "3-5": 24,
        "6-7": 23,
        "8-10": 22,
        "11-13": 21,
        "14-17": 20,
        "18-20": 19,
        "21-25": 18
      },
      {
        "gun_id": "us-16-1928",
        "nation": "US",
        "caliber_in": 16,
        "period": "1928",
        "1-2": 24,
        "3-5": 23,
        "6-7": 22,
        "8-10": 21,
        "11-13": 20,
        "14-17": 19,
        "18-20": 18,
        "21-25": 17
      },
      {
        "gun_id": "uk-15",
        "nation": "UK",
        "caliber_in": 15,
        "period": "all",
        "1-2": 19,
        "3-5": 18,
        "6-7": 18,
        "8-10": 18,
        "11-13": 17,
        "14-17": 17,
        "18-20": 17,
        "21-25": 16
      },
      {
        "gun_id": "us-14",
        "nation": "US",
        "caliber_in": 14,
        "period": "all",
        "1-2": 17,
        "3-5": 16,
        "6-7": 16,
        "8-10": 16,
        "11-13": 15,
        "14-17": 15,
        "18-20": 15,
        "21-25": 14
      },
      {
        "gun_id": "us-12",
        "nation": "US",
        "caliber_in": 12,
        "period": "all",
        "1-2": 20,
        "3-5": 18,
        "6-7": 17,
        "8-10": 15,
        "11-13": 14,
        "14-17": 12,
        "18-20": 11,
        "21-25": 9
      },
      {
        "gun_id": "generic-8",
        "nation": "GENERIC",
        "caliber_in": 8,
        "period": "all",
        "1-2": 13,
        "3-5": 12,
        "6-7": 11,
        "8-10": 10,
        "11-13": 9,
        "14-17": 8,
        "18-20": 7,
        "21-25": 6
      },
      {
        "gun_id": "uk-8",
        "nation": "UK",
        "caliber_in": 8,
        "period": "all",
        "1-2": 10,
        "3-5": 10,
        "6-7": 9,
        "8-10": 9,
        "11-13": 9,
        "14-17": 8,
        "18-20": 8,
        "21-25": 7
      },
      {
        "gun_id": "generic-7.5",
        "nation": "GENERIC",
        "caliber_in": 7.5,
        "period": "all",
        "1-2": 9,
        "3-5": 8,
        "6-7": 7,
        "8-10": 7,
        "11-13": 6,
        "14-17": 5,
        "18-20": 5,
        "21-25": 4
      },
      {
        "gun_id": "us-6",
        "nation": "US",
        "caliber_in": 6,
        "period": "all",
        "1-2": 9,
        "3-5": 8,
        "6-7": 7,
        "8-10": 7,
        "11-13": 6,
        "14-17": 5,
        "18-20": 5,
        "21-25": 4
      },
      {
        "gun_id": "uk-6",
        "nation": "UK",
        "caliber_in": 6,
        "period": "all",
        "1-2": 8,
        "3-5": 7,
        "6-7": 7,
        "8-10": 7,
        "11-13": 6,
        "14-17": 6,
        "18-20": 5,
        "21-25": 4
      },
      {
        "gun_id": "uk-5.25",
        "nation": "UK",
        "caliber_in": 5.25,
        "period": "all",
        "1-2": 7,
        "3-5": 7,
        "6-7": 7,
        "8-10": 6,
        "11-13": 6,
        "14-17": 5,
        "18-20": 4,
        "21-25": 4
      },
      {
        "gun_id": "us-5",
        "nation": "US",
        "caliber_in": 5,
        "period": "all",
        "1-2": 6,
        "3-5": 5,
        "6-7": 5,
        "8-10": 4,
        "11-13": 4,
        "14-17": 3,
        "18-20": 2,
        "21-25": 2
      },
      {
        "gun_id": "uk-4.7",
        "nation": "UK",
        "caliber_in": 4.7,
        "period": "all",
        "1-2": 6,
        "3-5": 6,
        "6-7": 6,
        "8-10": 5,
        "11-13": 5,
        "14-17": 4,
        "18-20": 3,
        "21-25": 3
      },
      {
        "gun_id": "generic-4.7-1928",
        "nation": "GENERIC",
        "caliber_in": 4.7,
        "period": "1928",
        "1-2": 5,
        "3-5": 5,
        "6-7": 4,
        "8-10": 4,
        "11-13": 3,
        "14-17": 3,
        "18-20": 2,
        "21-25": 2
      },
      {
        "gun_id": "generic-4.5-4-3.9",
        "nation": "GENERIC",
        "caliber_in": "4.5|4|3.9",
        "period": "all",
        "1-2": 5,
        "3-5": 5,
        "6-7": 4,
        "8-10": 4,
        "11-13": 3,
        "14-17": 3,
        "18-20": 2,
        "21-25": 2
      },
      {
        "gun_id": "us-4",
        "nation": "US",
        "caliber_in": 4,
        "period": "all",
        "1-2": 6,
        "3-5": 5,
        "6-7": 5,
        "8-10": 4,
        "11-13": 4,
        "14-17": 3,
        "18-20": 2,
        "21-25": 2
      },
      {
        "gun_id": "jp-18.1",
        "nation": "JP",
        "caliber_in": 18.1,
        "period": "all",
        "1-2": 26,
        "3-5": 25,
        "6-7": 24,
        "8-10": 23,
        "11-13": 22,
        "14-17": 21,
        "18-20": 20,
        "21-25": 19
      },
      {
        "gun_id": "jp-16.1",
        "nation": "JP",
        "caliber_in": 16.1,
        "period": "all",
        "1-2": 19,
        "3-5": 18,
        "6-7": 18,
        "8-10": 18,
        "11-13": 17,
        "14-17": 17,
        "18-20": 17,
        "21-25": 16
      },
      {
        "gun_id": "jp-14",
        "nation": "JP",
        "caliber_in": 14,
        "period": "all",
        "1-2": 17,
        "3-5": 16,
        "6-7": 16,
        "8-10": 16,
        "11-13": 15,
        "14-17": 15,
        "18-20": 15,
        "21-25": 14
      },
      {
        "gun_id": "jp-12.2",
        "nation": "JP",
        "caliber_in": 12.2,
        "period": "all",
        "1-2": 16,
        "3-5": 15,
        "6-7": 15,
        "8-10": 14,
        "11-13": 14,
        "14-17": 13,
        "18-20": 12,
        "21-25": 11
      },
      {
        "gun_id": "jp-7.9-8",
        "nation": "JP",
        "caliber_in": "7.9|8",
        "period": "all",
        "1-2": 10,
        "3-5": 10,
        "6-7": 9,
        "8-10": 9,
        "11-13": 9,
        "14-17": 8,
        "18-20": 8,
        "21-25": 7
      },
      {
        "gun_id": "jp-6.1",
        "nation": "JP",
        "caliber_in": 6.1,
        "period": "all",
        "1-2": 8,
        "3-5": 7,
        "6-7": 7,
        "8-10": 7,
        "11-13": 6,
        "14-17": 6,
        "18-20": 5,
        "21-25": 4
      },
      {
        "gun_id": "nl-se-5.9",
        "nation": "NL_SE",
        "caliber_in": 5.9,
        "period": "all",
        "1-2": 9,
        "3-5": 8,
        "6-7": 7,
        "8-10": 7,
        "11-13": 6,
        "14-17": 5,
        "18-20": 5,
        "21-25": 4
      },
      {
        "gun_id": "jp-5.5",
        "nation": "JP",
        "caliber_in": 5.5,
        "period": "all",
        "1-2": 7,
        "3-5": 7,
        "6-7": 7,
        "8-10": 6,
        "11-13": 6,
        "14-17": 5,
        "18-20": 4,
        "21-25": 4
      },
      {
        "gun_id": "jp-4.7",
        "nation": "JP",
        "caliber_in": 4.7,
        "period": "all",
        "1-2": 6,
        "3-5": 5,
        "6-7": 5,
        "8-10": 4,
        "11-13": 4,
        "14-17": 3,
        "18-20": 2,
        "21-25": 2
      },
      {
        "gun_id": "nl-4.7",
        "nation": "NL",
        "caliber_in": 4.7,
        "period": "all",
        "1-2": 6,
        "3-5": 6,
        "6-7": 6,
        "8-10": 5,
        "11-13": 5,
        "14-17": 4,
        "18-20": 3,
        "21-25": 3
      },
      {
        "gun_id": "de-3.5-us-jp-3",
        "nation": "DE_US_JP",
        "caliber_in": "3.5|3",
        "period": "all",
        "1-2": 4,
        "3-5": 3,
        "6-7": 2,
        "8-10": 2,
        "11-13": 1,
        "14-17": 1,
        "18-20": "-",
        "21-25": "-"
      }
    ],
    "d66Values": [11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26, 31, 32, 33, 34, 35, 36, 41, 42, 43, 44, 45, 46, 51, 52, 53, 54, 55, 56, 61, 62, 63, 64, 65, 66]
  }, ships: {
    "IBS-U-IJN-AOBA": {
      "id": "IBS-U-IJN-AOBA",
      "name": "青叶",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 12,
      "special_rules": []
    },
    "IBS-U-IJN-NAGATO": {
      "id": "IBS-U-IJN-NAGATO",
      "name": "长门",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [5, 5, 4],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 11.0,
        "secondary": null,
        "belt": 11.0,
        "bridge": 11.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 33,
      "special_rules": []
    },
    "IBS-U-IJN-MUTSU": {
      "id": "IBS-U-IJN-MUTSU",
      "name": "陆奥",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [5, 5, 4],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 11.0,
        "secondary": null,
        "belt": 11.0,
        "bridge": 11.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 32,
      "special_rules": []
    },
    "IBS-U-IJN-KAKO-I": {
      "id": "IBS-U-IJN-KAKO-I",
      "name": "加古(I)",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 7.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 7.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": 0.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 9,
      "special_rules": []
    },
    "IBS-U-USN-COLORADO": {
      "id": "IBS-U-USN-COLORADO",
      "name": "科罗拉多",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [4, 3, 2, 1],
        [3, 2, 1],
        [3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 18.0,
        "secondary": null,
        "belt": 13.0,
        "bridge": 16.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 31,
      "special_rules": []
    },
    "IBS-U-USN-WEST-VIRGINIA": {
      "id": "IBS-U-USN-WEST-VIRGINIA",
      "name": "西弗吉尼亚",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [4, 3, 2, 1],
        [3, 2, 1],
        [3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 18.0,
        "secondary": null,
        "belt": 13.0,
        "bridge": 16.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 30,
      "special_rules": []
    },
    "IBS-U-USN-OMAHA": {
      "id": "IBS-U-USN-OMAHA",
      "name": "奥马哈",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 6,
      "special_rules": []
    },
    "IBS-U-USN-MINNEAPOLIS": {
      "id": "IBS-U-USN-MINNEAPOLIS",
      "name": "明尼阿波利斯",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 3.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": true,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-NEW-ORLEANS": {
      "id": "IBS-U-USN-NEW-ORLEANS",
      "name": "新奥尔良",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 3.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": true,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-PENSACOLA": {
      "id": "IBS-U-USN-PENSACOLA",
      "name": "彭萨科拉",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-NORTHAMPTON": {
      "id": "IBS-U-USN-NORTHAMPTON",
      "name": "北安普敦",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-WASHINGTON": {
      "id": "IBS-U-USN-WASHINGTON",
      "name": "华盛顿",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [6, 6, 6],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 16.0,
        "secondary": 2.0,
        "belt": 12.0,
        "bridge": 15.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": true,
      "vp": 37,
      "special_rules": []
    },
    "IBS-U-USN-SOUTH-DAKOTA": {
      "id": "IBS-U-USN-SOUTH-DAKOTA",
      "name": "南达科塔",
      "ship_type": "BB",
      "displacement_band": "G",
      "hull_rows": [6, 6, 6],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 18.0,
        "secondary": 2.0,
        "belt": 12.0,
        "bridge": 16.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": true,
      "vp": 36,
      "special_rules": []
    },
    "IBS-U-IJN-FURUTAKA": {
      "id": "IBS-U-IJN-FURUTAKA",
      "name": "古鹰",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-IJN-KINUGASA": {
      "id": "IBS-U-IJN-KINUGASA",
      "name": "衣笠",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-IJN-FUBUKI": {
      "id": "IBS-U-IJN-FUBUKI",
      "name": "吹雪",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-HATSUYUKI": {
      "id": "IBS-U-IJN-HATSUYUKI",
      "name": "初雪",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-CHITOSE": {
      "id": "IBS-U-IJN-CHITOSE",
      "name": "千岁",
      "ship_type": "AV",
      "displacement_band": "B",
      "hull_rows": [4, 3, 3],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 12,
      "special_rules": [
        "primary_or_secondary_hit_becomes_1_hull"
      ]
    },
    "IBS-U-IJN-NISSHIN": {
      "id": "IBS-U-IJN-NISSHIN",
      "name": "日进",
      "ship_type": "AV",
      "displacement_band": "B",
      "hull_rows": [4, 3, 3],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 12,
      "special_rules": [
        "primary_or_secondary_hit_becomes_1_hull"
      ]
    },
    "IBS-U-IJN-ASAGUMO": {
      "id": "IBS-U-IJN-ASAGUMO",
      "name": "朝云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-NATSUGUMO": {
      "id": "IBS-U-IJN-NATSUGUMO",
      "name": "夏云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-YAMAGUMO": {
      "id": "IBS-U-IJN-YAMAGUMO",
      "name": "山云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-MURAKUMO": {
      "id": "IBS-U-IJN-MURAKUMO",
      "name": "丛云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-SHIRAYUKI": {
      "id": "IBS-U-IJN-SHIRAYUKI",
      "name": "白雪",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-AKIZUKI": {
      "id": "IBS-U-IJN-AKIZUKI",
      "name": "秋月",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-NIIZUKI": {
      "id": "IBS-U-IJN-NIIZUKI",
      "name": "新月",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-SUZUKAZE": {
      "id": "IBS-U-IJN-SUZUKAZE",
      "name": "凉风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-TANIKAZE": {
      "id": "IBS-U-IJN-TANIKAZE",
      "name": "谷风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-AMAGIRI": {
      "id": "IBS-U-IJN-AMAGIRI",
      "name": "天雾",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-HAMAKAZE": {
      "id": "IBS-U-IJN-HAMAKAZE",
      "name": "浜风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-NAGANAMI": {
      "id": "IBS-U-IJN-NAGANAMI",
      "name": "长波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-TAKANAMI": {
      "id": "IBS-U-IJN-TAKANAMI",
      "name": "高波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-MAKINAMI": {
      "id": "IBS-U-IJN-MAKINAMI",
      "name": "卷波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-KAGERO": {
      "id": "IBS-U-IJN-KAGERO",
      "name": "阳炎",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-KUROSHIO": {
      "id": "IBS-U-IJN-KUROSHIO",
      "name": "黑潮",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-OYASHIO": {
      "id": "IBS-U-IJN-OYASHIO",
      "name": "亲潮",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-KAWAKAZE": {
      "id": "IBS-U-IJN-KAWAKAZE",
      "name": "江风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-YUKIKAZE": {
      "id": "IBS-U-IJN-YUKIKAZE",
      "name": "雪风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-KIYONAMI": {
      "id": "IBS-U-IJN-KIYONAMI",
      "name": "清波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-YUGURE": {
      "id": "IBS-U-IJN-YUGURE",
      "name": "夕暮",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-TERUZUKI": {
      "id": "IBS-U-IJN-TERUZUKI",
      "name": "照月",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-YUDACHI": {
      "id": "IBS-U-IJN-YUDACHI",
      "name": "夕立",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-HARUSAME": {
      "id": "IBS-U-IJN-HARUSAME",
      "name": "春雨",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-INAZUMA": {
      "id": "IBS-U-IJN-INAZUMA",
      "name": "电",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-AKATSUKI": {
      "id": "IBS-U-IJN-AKATSUKI",
      "name": "晓",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-IKAZUCHI": {
      "id": "IBS-U-IJN-IKAZUCHI",
      "name": "雷",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-MURASAME": {
      "id": "IBS-U-IJN-MURASAME",
      "name": "村雨",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-SAMIDARE": {
      "id": "IBS-U-IJN-SAMIDARE",
      "name": "五月雨",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-AMATSU-KAZE": {
      "id": "IBS-U-IJN-AMATSU-KAZE",
      "name": "天津风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-URANAMI": {
      "id": "IBS-U-IJN-URANAMI",
      "name": "浦波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-AYANAMI": {
      "id": "IBS-U-IJN-AYANAMI",
      "name": "绫波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-SHIKINAMI": {
      "id": "IBS-U-IJN-SHIKINAMI",
      "name": "敷波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-HONOLULU": {
      "id": "IBS-U-USN-HONOLULU",
      "name": "火奴鲁鲁",
      "ship_type": "CL",
      "displacement_band": "C",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 6.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 12,
      "special_rules": []
    },
    "IBS-U-USN-ST-LOUIS": {
      "id": "IBS-U-USN-ST-LOUIS",
      "name": "圣路易斯",
      "ship_type": "CL",
      "displacement_band": "C",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 6.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-IJN-MIKAZUKI": {
      "id": "IBS-U-IJN-MIKAZUKI",
      "name": "三日月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [1, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type8",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-KAKO-II": {
      "id": "IBS-U-IJN-KAKO-II",
      "name": "加古(II)",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-IJN-CHOKAI": {
      "id": "IBS-U-IJN-CHOKAI",
      "name": "鸟海",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 15,
      "special_rules": []
    },
    "IBS-U-IJN-TENRYU": {
      "id": "IBS-U-IJN-TENRYU",
      "name": "天龙",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-YUBARI": {
      "id": "IBS-U-IJN-YUBARI",
      "name": "夕张",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "midships",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-USN-VINCENNES": {
      "id": "IBS-U-USN-VINCENNES",
      "name": "文森斯",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 3.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-QUINCY": {
      "id": "IBS-U-USN-QUINCY",
      "name": "昆西",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 3.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-ASTORIA": {
      "id": "IBS-U-USN-ASTORIA",
      "name": "阿斯托里亚",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 3.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-RAN-CANBERRA": {
      "id": "IBS-U-RAN-CANBERRA",
      "name": "堪培拉",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 4.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 4.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk7c",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-RAN-AUSTRALIA": {
      "id": "IBS-U-RAN-AUSTRALIA",
      "name": "澳大利亚",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 4.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 4.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk7c",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 12,
      "special_rules": []
    },
    "IBS-U-IJN-MYOKO": {
      "id": "IBS-U-IJN-MYOKO",
      "name": "妙高",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 16,
      "special_rules": []
    },
    "IBS-U-IJN-HAGURO": {
      "id": "IBS-U-IJN-HAGURO",
      "name": "羽黑",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 15,
      "special_rules": []
    },
    "IBS-U-IJN-SENDAI": {
      "id": "IBS-U-IJN-SENDAI",
      "name": "川内",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": 0.0,
        "belt": 2.0,
        "bridge": 0.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 7,
      "special_rules": []
    },
    "IBS-U-IJN-SHIGURE": {
      "id": "IBS-U-IJN-SHIGURE",
      "name": "时雨",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-HATSU-KAZE": {
      "id": "IBS-U-IJN-HATSU-KAZE",
      "name": "初风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-AGANO": {
      "id": "IBS-U-IJN-AGANO",
      "name": "阿贺野",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 8,
      "special_rules": []
    },
    "IBS-U-IJN-WAKATSUKI": {
      "id": "IBS-U-IJN-WAKATSUKI",
      "name": "若月",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-SATSUKI": {
      "id": "IBS-U-IJN-SATSUKI",
      "name": "皋月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [1, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type8",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-MINAZUKI": {
      "id": "IBS-U-IJN-MINAZUKI",
      "name": "水无月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [1, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type8",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-YUNAGI": {
      "id": "IBS-U-IJN-YUNAGI",
      "name": "夕凪",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [1, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-MATSU-KAZE": {
      "id": "IBS-U-IJN-MATSU-KAZE",
      "name": "松风",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [1, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-AKIGUMO": {
      "id": "IBS-U-IJN-AKIGUMO",
      "name": "秋云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-SAZANAMI": {
      "id": "IBS-U-IJN-SAZANAMI",
      "name": "涟",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-ISOKAZE": {
      "id": "IBS-U-IJN-ISOKAZE",
      "name": "矶风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-KAZEKUMO": {
      "id": "IBS-U-IJN-KAZEKUMO",
      "name": "风云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-YUGUMO": {
      "id": "IBS-U-IJN-YUGUMO",
      "name": "夕云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-FUMIZUKI": {
      "id": "IBS-U-IJN-FUMIZUKI",
      "name": "文月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [1, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-KAMIKAZE": {
      "id": "IBS-U-IJN-KAMIKAZE",
      "name": "神风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-IJN-OITE": {
      "id": "IBS-U-IJN-OITE",
      "name": "追风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-IJN-ASAKAZE": {
      "id": "IBS-U-IJN-ASAKAZE",
      "name": "朝风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-IJN-MUTSUKI": {
      "id": "IBS-U-IJN-MUTSUKI",
      "name": "睦月",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-UZUKI": {
      "id": "IBS-U-IJN-UZUKI",
      "name": "卯月",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-JINTSU-I": {
      "id": "IBS-U-IJN-JINTSU-I",
      "name": "神通(I)",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-IJN-TATSUTA": {
      "id": "IBS-U-IJN-TATSUTA",
      "name": "龙田",
      "ship_type": "CL",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "midships",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port",
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": 2.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-USN-BAINBRIDGE": {
      "id": "IBS-U-USN-BAINBRIDGE",
      "name": "班布里奇",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-DECATUR": {
      "id": "IBS-U-USN-DECATUR",
      "name": "迪凯特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-DAHLGREN": {
      "id": "IBS-U-USN-DAHLGREN",
      "name": "达尔格伦",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-TRUXTON": {
      "id": "IBS-U-USN-TRUXTON",
      "name": "特鲁斯顿",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-MCDONOUGH": {
      "id": "IBS-U-USN-MCDONOUGH",
      "name": "麦克多诺",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-PERRY": {
      "id": "IBS-U-USN-PERRY",
      "name": "佩里",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-HULL-I": {
      "id": "IBS-U-USN-HULL-I",
      "name": "赫尔(I)",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-FOX": {
      "id": "IBS-U-USN-FOX",
      "name": "福克斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 4.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-NICHOLAS": {
      "id": "IBS-U-USN-NICHOLAS",
      "name": "尼古拉斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-OBANNON": {
      "id": "IBS-U-USN-OBANNON",
      "name": "奥班农",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-TAYLOR": {
      "id": "IBS-U-USN-TAYLOR",
      "name": "泰勒",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-RADFORD": {
      "id": "IBS-U-USN-RADFORD",
      "name": "雷德福德",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-JENKINS": {
      "id": "IBS-U-USN-JENKINS",
      "name": "詹金斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-RALPH-TALBOT": {
      "id": "IBS-U-USN-RALPH-TALBOT",
      "name": "拉尔夫·托尔伯特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-GWIN": {
      "id": "IBS-U-USN-GWIN",
      "name": "葛文",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-MAURY": {
      "id": "IBS-U-USN-MAURY",
      "name": "莫里",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-WOODWORTH": {
      "id": "IBS-U-USN-WOODWORTH",
      "name": "伍德沃斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-FLETCHER": {
      "id": "IBS-U-USN-FLETCHER",
      "name": "弗莱彻",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-MONSSEN": {
      "id": "IBS-U-USN-MONSSEN",
      "name": "蒙森",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-AARON-WARD": {
      "id": "IBS-U-USN-AARON-WARD",
      "name": "亚伦沃德",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-BARTON": {
      "id": "IBS-U-USN-BARTON",
      "name": "巴顿",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-CUSHING": {
      "id": "IBS-U-USN-CUSHING",
      "name": "库欣",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-STERETT": {
      "id": "IBS-U-USN-STERETT",
      "name": "史特雷特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-BAGLEY": {
      "id": "IBS-U-USN-BAGLEY",
      "name": "巴格莱",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-PATTERSON": {
      "id": "IBS-U-USN-PATTERSON",
      "name": "帕特森",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-JARVIS": {
      "id": "IBS-U-USN-JARVIS",
      "name": "贾维斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-BLUE": {
      "id": "IBS-U-USN-BLUE",
      "name": "布鲁",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-RALPH-TALBOT-17": {
      "id": "IBS-U-USN-RALPH-TALBOT-17",
      "name": "拉尔夫·托尔伯特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-WILSON": {
      "id": "IBS-U-USN-WILSON",
      "name": "威尔逊",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-HELM": {
      "id": "IBS-U-USN-HELM",
      "name": "赫尔",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-HULL-II": {
      "id": "IBS-U-USN-HULL-II",
      "name": "赫尔(II)",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-DEWEY": {
      "id": "IBS-U-USN-DEWEY",
      "name": "杜威",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-ELLET": {
      "id": "IBS-U-USN-ELLET",
      "name": "埃利特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-SELFRIDGE": {
      "id": "IBS-U-USN-SELFRIDGE",
      "name": "赛尔弗里奇",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-USN-CHEVALIER": {
      "id": "IBS-U-USN-CHEVALIER",
      "name": "谢伐利埃",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-LA-VALLETTE": {
      "id": "IBS-U-USN-LA-VALLETTE",
      "name": "拉瓦利特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-DRAYTON": {
      "id": "IBS-U-USN-DRAYTON",
      "name": "德雷顿",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-PERKINS": {
      "id": "IBS-U-USN-PERKINS",
      "name": "帕金斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-LAMSON": {
      "id": "IBS-U-USN-LAMSON",
      "name": "拉姆森",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-LARDNER": {
      "id": "IBS-U-USN-LARDNER",
      "name": "拉德纳",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-WALKE": {
      "id": "IBS-U-USN-WALKE",
      "name": "沃克",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-BENHAM": {
      "id": "IBS-U-USN-BENHAM",
      "name": "本汉姆",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-PRESTON": {
      "id": "IBS-U-USN-PRESTON",
      "name": "普雷斯顿",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-CF-AUSBURNE": {
      "id": "IBS-U-USN-CF-AUSBURNE",
      "name": "查尔斯·奥斯本",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-DYSON": {
      "id": "IBS-U-USN-DYSON",
      "name": "戴森",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-STANLY": {
      "id": "IBS-U-USN-STANLY",
      "name": "斯坦立",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-CLAXTON": {
      "id": "IBS-U-USN-CLAXTON",
      "name": "克拉克斯顿",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-SPENCE": {
      "id": "IBS-U-USN-SPENCE",
      "name": "斯彭斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-THATCHER": {
      "id": "IBS-U-USN-THATCHER",
      "name": "撒切尔",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-CONVERSE": {
      "id": "IBS-U-USN-CONVERSE",
      "name": "康弗斯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-FOOTE": {
      "id": "IBS-U-USN-FOOTE",
      "name": "福特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-SAN-FRANCISCO": {
      "id": "IBS-U-USN-SAN-FRANCISCO",
      "name": "旧金山",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 8,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 3.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-BOISE": {
      "id": "IBS-U-USN-BOISE",
      "name": "博伊西",
      "ship_type": "CL",
      "displacement_band": "C",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": null,
        "belt": 5.0,
        "bridge": 5.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-SALT-LAKE-CITY": {
      "id": "IBS-U-USN-SALT-LAKE-CITY",
      "name": "盐湖城",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-HELENA": {
      "id": "IBS-U-USN-HELENA",
      "name": "海伦娜",
      "ship_type": "CL",
      "displacement_band": "C",
      "hull_rows": [5, 5, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 6.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-FARENHOLT": {
      "id": "IBS-U-USN-FARENHOLT",
      "name": "法伦霍尔特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-LAFFEY": {
      "id": "IBS-U-USN-LAFFEY",
      "name": "拉菲",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-DUNCAN": {
      "id": "IBS-U-USN-DUNCAN",
      "name": "邓肯",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-MCCALLA": {
      "id": "IBS-U-USN-MCCALLA",
      "name": "麦卡拉",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-BUCHANAN": {
      "id": "IBS-U-USN-BUCHANAN",
      "name": "布坎南",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-KM-KARL-GALSTER": {
      "id": "IBS-U-KM-KARL-GALSTER",
      "name": "卡尔加尔斯特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "de-nl-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 5,
      "special_rules": []
    },
    "IBS-U-KM-RICHARD-BEITZEN": {
      "id": "IBS-U-KM-RICHARD-BEITZEN",
      "name": "里夏德·拜茨恩",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "de-nl-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-KM-HANS-LODY": {
      "id": "IBS-U-KM-HANS-LODY",
      "name": "汉斯·洛迪",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "de-nl-21",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-RN-JAVELIN": {
      "id": "IBS-U-RN-JAVELIN",
      "name": "标枪",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk9",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-RN-KASHMIR": {
      "id": "IBS-U-RN-KASHMIR",
      "name": "克什米尔",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk9",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-RN-JERSEY": {
      "id": "IBS-U-RN-JERSEY",
      "name": "泽西",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk9",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-RN-JACKAL": {
      "id": "IBS-U-RN-JACKAL",
      "name": "豺",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk9",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-RN-JUPITER": {
      "id": "IBS-U-RN-JUPITER",
      "name": "朱庇特",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "uk-21-mk9",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-HIEI": {
      "id": "IBS-U-IJN-HIEI",
      "name": "比叡",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 4],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S6",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 9.0,
        "secondary": 6.0,
        "belt": 8.0,
        "bridge": 9.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 33,
      "special_rules": []
    },
    "IBS-U-IJN-KIRISHIMA": {
      "id": "IBS-U-IJN-KIRISHIMA",
      "name": "雾岛",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 4],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 14.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S6",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 9.0,
        "secondary": 6.0,
        "belt": 8.0,
        "bridge": 9.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 33,
      "special_rules": []
    },
    "IBS-U-IJN-AMAGI": {
      "id": "IBS-U-IJN-AMAGI",
      "name": "天城",
      "ship_type": "BC",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 3],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 12,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S6",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 10.0,
        "secondary": null,
        "belt": 9.0,
        "bridge": 13.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 32,
      "special_rules": []
    },
    "IBS-U-IJN-AKAGI": {
      "id": "IBS-U-IJN-AKAGI",
      "name": "赤城",
      "ship_type": "BC",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 3],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 12,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S6",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 10.0,
        "secondary": null,
        "belt": 9.0,
        "bridge": 13.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 32,
      "special_rules": []
    },
    "IBS-U-IJN-OWARI": {
      "id": "IBS-U-IJN-OWARI",
      "name": "尾张",
      "ship_type": "BC",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 3],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 12,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 13,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S6",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 10.0,
        "secondary": null,
        "belt": 10.0,
        "bridge": 13.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 33,
      "special_rules": []
    },
    "IBS-U-IJN-NACHI": {
      "id": "IBS-U-IJN-NACHI",
      "name": "那智",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 16,
      "special_rules": []
    },
    "IBS-U-IJN-TAKAO": {
      "id": "IBS-U-IJN-TAKAO",
      "name": "高雄",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT3",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT4",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 15,
      "special_rules": []
    },
    "IBS-U-IJN-ATAGO": {
      "id": "IBS-U-IJN-ATAGO",
      "name": "爱宕",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT3",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT4",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 15,
      "special_rules": []
    },
    "IBS-U-IJN-JINTSU-2": {
      "id": "IBS-U-IJN-JINTSU-2",
      "name": "神通Ⅱ",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P7",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT3",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT4",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 7,
      "special_rules": []
    },
    "IBS-U-IJN-NAGARA": {
      "id": "IBS-U-IJN-NAGARA",
      "name": "长良",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P7",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.5,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT3",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT4",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": 1.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 7,
      "special_rules": []
    },
    "IBS-U-IJN-SHIRATSUYU": {
      "id": "IBS-U-IJN-SHIRATSUYU",
      "name": "白露",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-ARASHI": {
      "id": "IBS-U-IJN-ARASHI",
      "name": "岚",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-HAGIKAZE": {
      "id": "IBS-U-IJN-HAGIKAZE",
      "name": "萩风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-ONAMI": {
      "id": "IBS-U-IJN-ONAMI",
      "name": "大波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type90",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-UZUKI-2": {
      "id": "IBS-U-IJN-UZUKI-2",
      "name": "卯月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [2, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type8",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-NAGATSUKI": {
      "id": "IBS-U-IJN-NAGATSUKI",
      "name": "长月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [2, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type8",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-IJN-MONCHIZUKI": {
      "id": "IBS-U-IJN-MONCHIZUKI",
      "name": "望月",
      "ship_type": "APD",
      "displacement_band": "A",
      "hull_rows": [2, 1, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 4.7,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 4.7,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type8",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R03": {
      "id": "IBS-U-USN-UNNAMED-T01-R03",
      "name": "北卡罗来纳",
      "ship_type": "BB",
      "displacement_band": "F",
      "hull_rows": [6, 6, 5, 5, 5],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 36,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 36,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 36,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 16.0,
        "secondary": 2.0,
        "belt": 12.0,
        "bridge": 15.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": true,
      "vp": 37,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R06": {
      "id": "IBS-U-USN-UNNAMED-T01-R06",
      "name": "列克星敦",
      "ship_type": "BC",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk11-model3-1928",
      "armour": {
        "primary": 14.0,
        "secondary": null,
        "belt": 7.0,
        "bridge": 16.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 31,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R07": {
      "id": "IBS-U-USN-UNNAMED-T01-R07",
      "name": "合众国",
      "ship_type": "BC",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk11-model3-1928",
      "armour": {
        "primary": 14.0,
        "secondary": null,
        "belt": 7.0,
        "bridge": 16.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 31,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R08": {
      "id": "IBS-U-USN-UNNAMED-T01-R08",
      "name": "宪法",
      "ship_type": "BC",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 14,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk11-model3-1928",
      "armour": {
        "primary": 14.0,
        "secondary": null,
        "belt": 7.0,
        "bridge": 16.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 31,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R12": {
      "id": "IBS-U-USN-UNNAMED-T01-R12",
      "name": "芝加哥",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 8,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R13": {
      "id": "IBS-U-USN-UNNAMED-T01-R13",
      "name": "休斯顿",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 8,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 4.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R20": {
      "id": "IBS-U-USN-UNNAMED-T01-R20",
      "name": "波特兰",
      "ship_type": "CA",
      "displacement_band": "C",
      "hull_rows": [4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 8,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 2.0,
        "bridge": 1.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R22": {
      "id": "IBS-U-USN-UNNAMED-T01-R22",
      "name": "孟菲斯",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [3, 3, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "midships",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "midships",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk11-model3-1928",
      "armour": {
        "primary": 2.0,
        "secondary": null,
        "belt": 3.0,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": true,
      "vp": 6,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R23": {
      "id": "IBS-U-USN-UNNAMED-T01-R23",
      "name": "亚特兰大",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [4, 3, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": 1.0,
        "secondary": 1.0,
        "belt": 3.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 8,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R24": {
      "id": "IBS-U-USN-UNNAMED-T01-R24",
      "name": "朱诺",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [4, 3, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": 1.0,
        "secondary": 1.0,
        "belt": 3.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 8,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R25": {
      "id": "IBS-U-USN-UNNAMED-T01-R25",
      "name": "圣胡安",
      "ship_type": "CL",
      "displacement_band": "B",
      "hull_rows": [4, 3, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": 1.0,
        "secondary": 1.0,
        "belt": 3.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 8,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R26": {
      "id": "IBS-U-USN-UNNAMED-T01-R26",
      "name": "克利夫兰",
      "ship_type": "CL",
      "displacement_band": "D",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 5.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R27": {
      "id": "IBS-U-USN-UNNAMED-T01-R27",
      "name": "哥伦比亚",
      "ship_type": "CL",
      "displacement_band": "D",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 5.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R28": {
      "id": "IBS-U-USN-UNNAMED-T01-R28",
      "name": "蒙彼利埃",
      "ship_type": "CL",
      "displacement_band": "D",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 5.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R29": {
      "id": "IBS-U-USN-UNNAMED-T01-R29",
      "name": "丹弗",
      "ship_type": "CL",
      "displacement_band": "D",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 7,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 6.0,
        "secondary": 1.0,
        "belt": 5.0,
        "bridge": 5.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 11,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R51": {
      "id": "IBS-U-USN-UNNAMED-T01-R51",
      "name": "邓拉普",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "midships",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-USN-UNNAMED-T01-R52": {
      "id": "IBS-U-USN-UNNAMED-T01-R52",
      "name": "格里德利",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 1],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 1,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-P2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        },
        {
          "id": "TT-S2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 2,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-YAMATO": {
      "id": "IBS-U-IJN-ERMA-YAMATO",
      "name": "大和",
      "ship_type": "BB",
      "displacement_band": "I",
      "hull_rows": [9, 9, 9],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.1,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "T-P1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P2",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P3",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P4",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P5",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P6",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-S1",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S3",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S4",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S5",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S6",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 24.0,
        "secondary": 6.0,
        "belt": 16.0,
        "bridge": 18.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 66,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-MUSASHI": {
      "id": "IBS-U-IJN-ERMA-MUSASHI",
      "name": "武藏",
      "ship_type": "BB",
      "displacement_band": "I",
      "hull_rows": [9, 9, 9],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.1,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "T-P1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P2",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P3",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P4",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P5",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P6",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-S1",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S3",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S4",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S5",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S6",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 24.0,
        "secondary": 6.0,
        "belt": 16.0,
        "bridge": 18.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 65,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-SHINANO": {
      "id": "IBS-U-IJN-ERMA-SHINANO",
      "name": "信浓",
      "ship_type": "BB",
      "displacement_band": "I",
      "hull_rows": [9, 9, 9],
      "speed_damage_track": [
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 45,
          "caliber": 18.1,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 6,
          "caliber": 6.1,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 6,
          "caliber": 6.1,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "T-P1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P2",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P3",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P4",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P5",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P6",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-S1",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S3",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S4",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S5",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S6",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 24.0,
        "secondary": 6.0,
        "belt": 16.0,
        "bridge": 18.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 65,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-AZUMA": {
      "id": "IBS-U-IJN-ERMA-AZUMA",
      "name": "吾妻",
      "ship_type": "CB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 23,
          "caliber": 12.2,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 23,
          "caliber": 12.2,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 23,
          "caliber": 12.2,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P4",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 13.0,
        "secondary": 2.0,
        "belt": 8.3,
        "bridge": 8.3
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 32,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-ISHIKARI": {
      "id": "IBS-U-IJN-ERMA-ISHIKARI",
      "name": "石狩",
      "ship_type": "CB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 23,
          "caliber": 12.2,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 23,
          "caliber": 12.2,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 23,
          "caliber": 12.2,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P4",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT-P2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT-S2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 13.0,
        "secondary": 2.0,
        "belt": 8.3,
        "bridge": 8.3
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 32,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-IBUKI": {
      "id": "IBS-U-IJN-ERMA-IBUKI",
      "name": "伊吹",
      "ship_type": "CA",
      "displacement_band": "D",
      "hull_rows": [5, 5, 5],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT-P2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT-S2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": 0.0,
        "belt": 4.0,
        "bridge": 4.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 16,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-KURAMA": {
      "id": "IBS-U-IJN-ERMA-KURAMA",
      "name": "鞍马",
      "ship_type": "CA",
      "displacement_band": "D",
      "hull_rows": [5, 5, 5],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 6,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.9,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P1",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 3,
          "reloads": 3
        },
        {
          "id": "TT-P2",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 1,
          "reloads": 1
        },
        {
          "id": "TT-C",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 3
        },
        {
          "id": "TT-S1",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 3
        },
        {
          "id": "TT-S2",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 1,
          "reloads": 1
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": 0.0,
        "belt": 4.0,
        "bridge": 4.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 16,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-GOKASE": {
      "id": "IBS-U-IJN-ERMA-GOKASE",
      "name": "五濑",
      "ship_type": "CL",
      "displacement_band": "C",
      "hull_rows": [4, 3, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 4,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT-P",
          "position": "port",
          "arcs": [
            "port"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT-S",
          "position": "starboard",
          "arcs": [
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": 1.0,
        "secondary": 0.0,
        "belt": 2.0,
        "bridge": 2.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 10,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-SHIMAKAZE": {
      "id": "IBS-U-IJN-ERMA-SHIMAKAZE",
      "name": "岛风",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [3, 2, 2],
      "speed_damage_track": [
        [7, 6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        },
        {
          "id": "TT3",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 7,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-KAZEGUMO": {
      "id": "IBS-U-IJN-ERMA-KAZEGUMO",
      "name": "风云",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-NAGANAMI": {
      "id": "IBS-U-IJN-ERMA-NAGANAMI",
      "name": "长波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 2
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-IJN-ERMA-MAKINAMI": {
      "id": "IBS-U-IJN-ERMA-MAKINAMI",
      "name": "卷波",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [2, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 2,
          "reloads": 0
        }
      ],
      "torpedo_type": "jp-24-type93",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": false,
      "aircraft": false,
      "vp": 4,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-IOWA": {
      "id": "IBS-U-USN-ERMA-IOWA",
      "name": "衣阿华",
      "ship_type": "BB",
      "displacement_band": "H",
      "hull_rows": [7, 7, 7],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P4",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P5",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 17.0,
        "secondary": 1.0,
        "belt": 13.0,
        "bridge": 17.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 44,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-NEW-JERSEY": {
      "id": "IBS-U-USN-ERMA-NEW-JERSEY",
      "name": "新泽西",
      "ship_type": "BB",
      "displacement_band": "H",
      "hull_rows": [7, 7, 7],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P4",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P5",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 17.0,
        "secondary": 1.0,
        "belt": 13.0,
        "bridge": 17.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 43,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-MISSOURI": {
      "id": "IBS-U-USN-ERMA-MISSOURI",
      "name": "密苏里",
      "ship_type": "BB",
      "displacement_band": "H",
      "hull_rows": [7, 7, 7],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P4",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P5",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 17.0,
        "secondary": 1.0,
        "belt": 13.0,
        "bridge": 17.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 43,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-WISCONSIN": {
      "id": "IBS-U-USN-ERMA-WISCONSIN",
      "name": "威斯康星",
      "ship_type": "BB",
      "displacement_band": "H",
      "hull_rows": [7, 7, 7],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 38,
          "caliber": 16.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P4",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P5",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S4",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S5",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 17.0,
        "secondary": 1.0,
        "belt": 13.0,
        "bridge": 17.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 43,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-ALASKA": {
      "id": "IBS-U-USN-ERMA-ALASKA",
      "name": "阿拉斯加",
      "ship_type": "CB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 24,
          "caliber": 12.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 24,
          "caliber": 12.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 24,
          "caliber": 12.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 13.0,
        "secondary": 1.0,
        "belt": 9.5,
        "bridge": 9.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 30,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-GUAM": {
      "id": "IBS-U-USN-ERMA-GUAM",
      "name": "关岛",
      "ship_type": "CB",
      "displacement_band": "F",
      "hull_rows": [4, 4, 4, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 24,
          "caliber": 12.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 24,
          "caliber": 12.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 24,
          "caliber": 12.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 13.0,
        "secondary": 1.0,
        "belt": 9.5,
        "bridge": 9.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 30,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-DES-MOINES": {
      "id": "IBS-U-USN-ERMA-DES-MOINES",
      "name": "得梅因",
      "ship_type": "CA",
      "displacement_band": "D",
      "hull_rows": [4, 3, 3, 3, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 20,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 20,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 20,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "T-P1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P2",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P3",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P4",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-S1",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S3",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S4",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": 1.0,
        "belt": 6.0,
        "bridge": 6.5
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 16,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-SALEM": {
      "id": "IBS-U-USN-ERMA-SALEM",
      "name": "塞勒姆",
      "ship_type": "CA",
      "displacement_band": "D",
      "hull_rows": [4, 3, 3, 3, 3],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 20,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 20,
          "caliber": 8.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 20,
          "caliber": 8.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 2,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "T-P1",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P2",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P3",
          "kind": "tertiary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-P4",
          "kind": "tertiary",
          "position": "port",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "T-S1",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S2",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S3",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "T-S4",
          "kind": "tertiary",
          "position": "starboard",
          "firepower": 3,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 8.0,
        "secondary": 1.0,
        "belt": 6.0,
        "bridge": 6.5
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 16,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-WORCESTER": {
      "id": "IBS-U-USN-ERMA-WORCESTER",
      "name": "伍斯特",
      "ship_type": "CL",
      "displacement_band": "D",
      "hull_rows": [5, 4, 4],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "bow",
          "firepower": 5,
          "caliber": 6.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P4",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P5",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "P6",
          "kind": "primary",
          "position": "stern",
          "firepower": 5,
          "caliber": 6.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        },
        {
          "id": "S1",
          "kind": "secondary",
          "position": "bow",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "S-P1",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P2",
          "kind": "secondary",
          "position": "port",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-P3",
          "kind": "secondary",
          "position": "port",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "port"
          ]
        },
        {
          "id": "S-S1",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S2",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S-S3",
          "kind": "secondary",
          "position": "starboard",
          "firepower": 2,
          "caliber": 3.0,
          "arcs": [
            "starboard"
          ]
        },
        {
          "id": "S2",
          "kind": "secondary",
          "position": "stern",
          "firepower": 1,
          "caliber": 3.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [],
      "torpedo_type": null,
      "armour": {
        "primary": 5.0,
        "secondary": 0.0,
        "belt": 5.0,
        "bridge": 5.0
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 12,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-ALLEN-M-SUMNER": {
      "id": "IBS-U-USN-ERMA-ALLEN-M-SUMNER",
      "name": "艾伦·M·萨姆纳",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [3, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-INGRAHAM": {
      "id": "IBS-U-USN-ERMA-INGRAHAM",
      "name": "英格拉罕",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [3, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    },
    "IBS-U-USN-ERMA-COOPER": {
      "id": "IBS-U-USN-ERMA-COOPER",
      "name": "库珀",
      "ship_type": "DD",
      "displacement_band": "A",
      "hull_rows": [3, 2, 2],
      "speed_damage_track": [
        [6, 5, 4, 3, 2, 1],
        [6, 5, 4, 3, 2, 1],
        [5, 4, 3, 2, 1]
      ],
      "guns": [
        {
          "id": "P1",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P2",
          "kind": "primary",
          "position": "bow",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "bow",
            "port",
            "starboard"
          ]
        },
        {
          "id": "P3",
          "kind": "primary",
          "position": "stern",
          "firepower": 3,
          "caliber": 5.0,
          "arcs": [
            "port",
            "starboard",
            "stern"
          ]
        }
      ],
      "torpedo_launchers": [
        {
          "id": "TT1",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        },
        {
          "id": "TT2",
          "position": "midships",
          "arcs": [
            "port",
            "starboard"
          ],
          "torpedoes": 3,
          "reloads": 0
        }
      ],
      "torpedo_type": "us-21-mk15-1942",
      "armour": {
        "primary": null,
        "secondary": null,
        "belt": null,
        "bridge": null
      },
      "fire_control": true,
      "radar": true,
      "aircraft": false,
      "vp": 3,
      "special_rules": []
    }
  }, scenarios: {
    "IBS-S-01": {
      "id": "IBS-S-01",
      "number": 1,
      "title": "埃斯佩兰斯角海战",
      "date": "1942-10-11",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 1,
        "printed_page": 2,
        "status": "verified_source"
      },
      "turns": 7,
      "visibility": {
        "axis": 16,
        "allies": 14
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "initial_phase": "gunnery",
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_7"
      },
      "special_rules": [
        {
          "id": "IBS-S-01-R1",
          "text": "第一回合从炮击执行阶段开始；移动已完成。"
        },
        {
          "id": "IBS-S-01-R2",
          "text": "日军第一回合不得炮击。"
        },
        {
          "id": "IBS-S-01-R3",
          "text": "日军第四回合之前不得发射鱼雷。"
        },
        {
          "id": "IBS-S-01-R4",
          "text": "美军火控不佳；所有阶段、所有攻击的 GF 减半并向上取整。"
        },
        {
          "id": "IBS-S-01-R5",
          "text": "第三回合开始时掷一次 1D6；结果为 1 时，日军增援在第四回合开始、移动计划前从 E17 至 U27 间入场。"
        },
        {
          "id": "IBS-S-01-R6",
          "text": "除朝云外，所有增援驱逐舰划去全部鱼雷备雷。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-01-R2",
          "kind": "turn_restriction",
          "sides": [
            "axis"
          ],
          "turns": [1],
          "actions": [
            "gunnery"
          ],
          "reason": "想定特例：日军第 1 回合不得炮击"
        },
        {
          "id": "IBS-S-01-R3",
          "kind": "turn_restriction",
          "sides": [
            "axis"
          ],
          "turns": [1, 2, 3],
          "actions": [
            "torpedo"
          ],
          "reason": "想定特例：日军第 4 回合前不得发射鱼雷"
        },
        {
          "id": "IBS-S-01-R4",
          "kind": "firepower_multiplier",
          "sides": [
            "allies"
          ],
          "factor": 0.5,
          "ceil": true,
          "note": "美军火控不佳：所有阶段、所有攻击的 GF 减半并向上取整"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-AOBA",
          "name": "青叶",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "P10",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-青叶.png"
        },
        {
          "id": "IBS-U-IJN-FURUTAKA",
          "name": "古鹰",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "N9",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-古鹰.png"
        },
        {
          "id": "IBS-U-IJN-KINUGASA",
          "name": "衣笠",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "L8",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-衣笠.png"
        },
        {
          "id": "IBS-U-IJN-FUBUKI",
          "name": "吹雪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "P14",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-吹雪.png"
        },
        {
          "id": "IBS-U-IJN-HATSUYUKI",
          "name": "初雪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "R7",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-初雪.png"
        },
        {
          "id": "IBS-U-USN-FARENHOLT",
          "name": "法伦霍尔特",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "V12",
          "heading": 4,
          "speed": 5,
          "asset": "美国-DD-法伦霍尔特.png"
        },
        {
          "id": "IBS-U-USN-LAFFEY",
          "name": "拉菲",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X11",
          "heading": 4,
          "speed": 5,
          "asset": "美国-DD-拉菲.png"
        },
        {
          "id": "IBS-U-USN-SAN-FRANCISCO",
          "name": "旧金山",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "V14",
          "heading": 4,
          "speed": 3,
          "asset": "美国-CA-旧金山.png"
        },
        {
          "id": "IBS-U-USN-BOISE",
          "name": "博伊西",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "W14",
          "heading": 4,
          "speed": 3,
          "asset": "美国-CL-博伊西.png"
        },
        {
          "id": "IBS-U-USN-SALT-LAKE-CITY",
          "name": "盐湖城",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "X13",
          "heading": 4,
          "speed": 3,
          "asset": "美国-CA-盐湖城.png"
        },
        {
          "id": "IBS-U-USN-HELENA",
          "name": "海伦娜",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "Y13",
          "heading": 4,
          "speed": 3,
          "asset": "美国-CL-海伦娜.png"
        },
        {
          "id": "IBS-U-USN-BUCHANAN",
          "name": "布坎南",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z12",
          "heading": 4,
          "speed": 3,
          "asset": "美国-DD-布坎南.png"
        },
        {
          "id": "IBS-U-USN-MCCALLA",
          "name": "麦卡拉",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "AA12",
          "heading": 4,
          "speed": 3,
          "asset": "美国-DD-麦卡拉.png"
        },
        {
          "id": "IBS-U-USN-DUNCAN",
          "name": "邓肯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X8",
          "heading": 4,
          "speed": 5,
          "asset": "美国-DD-邓肯.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 3,
          "roll": "1d6",
          "succeeds_on": [1]
        },
        "arrival": {
          "turn": 4,
          "timing": "before_movement_planning",
          "entry_hex_range": [
            "E17",
            "U27"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-IJN-CHITOSE",
            "name": "千岁",
            "side": "axis",
            "template": "av-japanese-1942",
            "speed_track": [5, 5, 4],
            "asset": "日本-AV-千岁.png"
          },
          {
            "id": "IBS-U-IJN-NISSHIN",
            "name": "日进",
            "side": "axis",
            "template": "av-japanese-1942",
            "speed_track": [5, 5, 4],
            "asset": "日本-AV-日进.png"
          },
          {
            "id": "IBS-U-IJN-ASAGUMO",
            "name": "朝云",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "retain_torpedo_reloads": true,
            "asset": "日本-DD-朝云.png"
          },
          {
            "id": "IBS-U-IJN-NATSUGUMO",
            "name": "夏云",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "torpedo_reloads": 0,
            "asset": "日本-DD-夏云.png"
          },
          {
            "id": "IBS-U-IJN-YAMAGUMO",
            "name": "山云",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "torpedo_reloads": 0,
            "asset": "日本-DD-山云.png"
          },
          {
            "id": "IBS-U-IJN-SHIRAYUKI",
            "name": "白雪",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "torpedo_reloads": 0,
            "asset": "日本-DD-白雪.png"
          },
          {
            "id": "IBS-U-IJN-MURAKUMO",
            "name": "丛云",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "torpedo_reloads": 0,
            "asset": "日本-DD-丛云.png"
          },
          {
            "id": "IBS-U-IJN-AKIZUKI",
            "name": "秋月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 5, 5],
            "torpedo_reloads": 0,
            "asset": "日本-DD-秋月.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 0,
        "allies_wins": 4,
        "draws": 6,
        "avg_turns": 7,
        "avg_sunk": {
          "axis": 2.9,
          "allies": 1.3
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-02": {
      "id": "IBS-S-02",
      "number": 2,
      "title": "库拉湾海战",
      "date": "1943-07-06",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 2,
        "printed_page": 3,
        "status": "verified_source"
      },
      "turns": 9,
      "visibility": {
        "axis": 16,
        "allies": 12
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；一般模式与真实模式部署仍以 ships 初始位置和想定规则为权威。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-strike-1",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-NIIZUKI",
                "IBS-U-IJN-SUZUKAZE",
                "IBS-U-IJN-TANIKAZE"
              ],
              "note": "第一突击队（警戒列）"
            },
            {
              "id": "axis-transport-2",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-AMAGIRI",
                "IBS-U-IJN-HATSUYUKI",
                "IBS-U-IJN-NAGATSUKI",
                "IBS-U-IJN-SATSUKI"
              ],
              "note": "第二输送队（东京快车）"
            }
          ],
          "allies": [
            {
              "id": "allies-tf36-1",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-NICHOLAS",
                "IBS-U-USN-OBANNON",
                "IBS-U-USN-HONOLULU",
                "IBS-U-USN-HELENA",
                "IBS-U-USN-ST-LOUIS",
                "IBS-U-USN-JENKINS",
                "IBS-U-USN-RADFORD"
              ],
              "note": "TF36.1 安斯沃思单纵队：驱逐前卫-巡洋舰-驱逐后卫"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_9"
      },
      "special_rules": [
        {
          "id": "IBS-S-02-R1",
          "text": "游戏回合：9个回合，或所有日军单位离开地图。"
        },
        {
          "id": "IBS-S-02-R2",
          "text": "岛屿放置：将萨沃岛小地图的X格对应放置在A-27格。"
        },
        {
          "id": "IBS-S-02-R3",
          "text": "根据海军条令，美军DD必须始终维持与CL相邻。"
        },
        {
          "id": "IBS-S-02-R4",
          "text": "日军可能受到增援。仅在第4回合开始时掷1枚骰子，如果掷到1或2，那么增援单位在移动阶段，以任意航速从G27至O27进入地图。“浜风”、“望月”、“三日月”按此顺序单纵队编队，划掉“浜风”的鱼雷再装填，因为它装载了额外的集装箱物资。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-02-R3",
          "kind": "movement_constraint",
          "constraint": "stay_adjacent",
          "max_distance": 2,
          "note": "美军 DD 移动结束时必须与己方 CL 相邻（无存活 CL 时不适用）",
          "subjects": {
            "sides": [
              "allies"
            ],
            "ship_types": [
              "DD"
            ]
          },
          "anchors": {
            "sides": [
              "allies"
            ],
            "ship_types": [
              "CL"
            ]
          }
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-NIIZUKI",
          "name": "新月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K14",
          "heading": 6,
          "speed": 5,
          "asset": "日本-DD-新月.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-SUZUKAZE",
          "name": "凉风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K15",
          "heading": 6,
          "speed": 5,
          "asset": "日本-DD-凉风.png"
        },
        {
          "id": "IBS-U-IJN-TANIKAZE",
          "name": "谷风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K16",
          "heading": 6,
          "speed": 5,
          "asset": "日本-DD-谷风.png"
        },
        {
          "id": "IBS-U-IJN-AMAGIRI",
          "name": "天雾",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H21",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-天雾.png"
        },
        {
          "id": "IBS-U-IJN-HATSUYUKI",
          "name": "初雪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H20",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-初雪.png"
        },
        {
          "id": "IBS-U-IJN-NAGATSUKI",
          "name": "长月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H19",
          "heading": 3,
          "speed": 5,
          "asset": "日本-APD-长月.png"
        },
        {
          "id": "IBS-U-IJN-SATSUKI",
          "name": "皋月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H18",
          "heading": 3,
          "speed": 5,
          "asset": "日本-APD-皋月.png"
        },
        {
          "id": "IBS-U-USN-NICHOLAS",
          "name": "尼古拉斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "T6",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-尼古拉斯.png"
        },
        {
          "id": "IBS-U-USN-OBANNON",
          "name": "奥班农",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "U7",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-奥班农.png"
        },
        {
          "id": "IBS-U-USN-HONOLULU",
          "name": "火奴鲁鲁",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "V7",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-火奴鲁鲁.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-HELENA",
          "name": "海伦娜",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "W8",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-海伦娜.png"
        },
        {
          "id": "IBS-U-USN-ST-LOUIS",
          "name": "圣路易斯",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "X8",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-圣路易斯.png"
        },
        {
          "id": "IBS-U-USN-JENKINS",
          "name": "詹金斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y9",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-詹金斯.png"
        },
        {
          "id": "IBS-U-USN-RADFORD",
          "name": "雷德福德",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z9",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-雷德福德.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 4,
          "roll": "1d6",
          "succeeds_on": [1, 2]
        },
        "arrival": {
          "turn": 4,
          "timing": "during_movement",
          "entry_hex_range": [
            "G27",
            "O27"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-IJN-HAMAKAZE",
            "name": "浜风",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "torpedo_reloads": 0,
            "asset": "日本-DD-浜风.png"
          },
          {
            "id": "IBS-U-IJN-MONCHIZUKI",
            "name": "望月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 5, 5],
            "asset": "日本-APD-望月.png"
          },
          {
            "id": "IBS-U-IJN-MIKAZUKI",
            "name": "三日月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 5, 5],
            "asset": "日本-APD-三日月.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 5,
        "allies_wins": 2,
        "draws": 3,
        "avg_turns": 8.2,
        "avg_sunk": {
          "axis": 1.2,
          "allies": 1.3
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-03": {
      "id": "IBS-S-03",
      "number": 3,
      "title": "通道行动",
      "date": "1940-11-28",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 3,
        "printed_page": 4,
        "status": "verified_source"
      },
      "turns": 4,
      "visibility": {
        "axis": 4,
        "allies": 4
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "victory": {
        "kind": "scenario_03_thresholds",
        "evaluated_at": "end_of_turn_4",
        "british": {
          "tactical": "击沉或把至少一艘德国 DD 的速度降至 2-2-2 或更低。",
          "strategic": "击沉或把多艘德国 DD 的速度降至 2-2-2 或更低。"
        },
        "german": {
          "tactical": "没有德国 DD 被击沉或被降速至 2-2-2 或更低。",
          "minor_strategic": "在满足战术胜利前提下，另击沉至少两艘英国 DD。"
        }
      },
      "ships": [
        {
          "id": "IBS-U-KM-KARL-GALSTER",
          "name": "卡尔加尔斯特",
          "side": "axis",
          "template": "dd-german-1940",
          "position": "O14",
          "heading": 4,
          "speed": 5,
          "asset": "德国-DD-卡尔加尔斯特.png"
        },
        {
          "id": "IBS-U-KM-RICHARD-BEITZEN",
          "name": "里夏德·拜茨恩",
          "side": "axis",
          "template": "dd-german-1940",
          "position": "P13",
          "heading": 4,
          "speed": 5,
          "asset": "德国-DD-里夏德·拜茨恩.png"
        },
        {
          "id": "IBS-U-KM-HANS-LODY",
          "name": "汉斯·洛迪",
          "side": "axis",
          "template": "dd-german-1940",
          "position": "R12",
          "heading": 4,
          "speed": 5,
          "asset": "德国-DD-汉斯·洛迪.png"
        },
        {
          "id": "IBS-U-RN-JAVELIN",
          "name": "标枪",
          "side": "allies",
          "template": "dd-british-1940",
          "position": "R16",
          "heading": 5,
          "speed": 5,
          "asset": "英国-DD-标枪.png"
        },
        {
          "id": "IBS-U-RN-KASHMIR",
          "name": "克什米尔",
          "side": "allies",
          "template": "dd-british-1940",
          "position": "S16",
          "heading": 5,
          "speed": 5,
          "asset": "英国-DD-克什米尔.png"
        },
        {
          "id": "IBS-U-RN-JERSEY",
          "name": "泽西",
          "side": "allies",
          "template": "dd-british-1940",
          "position": "T15",
          "heading": 5,
          "speed": 5,
          "asset": "英国-DD-泽西.png"
        },
        {
          "id": "IBS-U-RN-JACKAL",
          "name": "豺",
          "side": "allies",
          "template": "dd-british-1940",
          "position": "U15",
          "heading": 5,
          "speed": 5,
          "asset": "英国-DD-豺.png"
        },
        {
          "id": "IBS-U-RN-JUPITER",
          "name": "朱庇特",
          "side": "allies",
          "template": "dd-british-1940",
          "position": "V14",
          "heading": 5,
          "speed": 5,
          "asset": "英国-DD-朱庇特.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 6,
        "allies_wins": 4,
        "draws": 0,
        "avg_turns": 4,
        "avg_sunk": {
          "axis": 0.7,
          "allies": 0.6
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-04": {
      "id": "IBS-S-04",
      "number": 4,
      "title": "塔萨法隆格海战",
      "date": "1942-11-30",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 4,
        "printed_page": 5,
        "status": "verified_source"
      },
      "turns": 6,
      "visibility": {
        "axis": 13,
        "allies": 11
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；一般模式与真实模式部署仍以 ships 初始位置和想定规则为权威。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-tanaka-strike",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-NAGANAMI",
                "IBS-U-IJN-TAKANAMI",
                "IBS-U-IJN-MAKINAMI",
                "IBS-U-IJN-KAGERO",
                "IBS-U-IJN-KUROSHIO",
                "IBS-U-IJN-OYASHIO",
                "IBS-U-IJN-KAWAKAZE",
                "IBS-U-IJN-SUZUKAZE"
              ],
              "note": "田中赖三驱逐突击队单纵（龙岩作战）"
            }
          ],
          "allies": [
            {
              "id": "allies-van-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-FLETCHER",
                "IBS-U-USN-PERKINS",
                "IBS-U-USN-MAURY",
                "IBS-U-USN-DRAYTON"
              ],
              "note": "前卫驱逐队"
            },
            {
              "id": "allies-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-MINNEAPOLIS",
                "IBS-U-USN-NEW-ORLEANS",
                "IBS-U-USN-PENSACOLA",
                "IBS-U-USN-HONOLULU",
                "IBS-U-USN-NORTHAMPTON"
              ],
              "note": "第67.4特混大队巡洋舰纵列（赖特少将旗舰明尼阿波利斯）"
            },
            {
              "id": "allies-rear-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-LAMSON",
                "IBS-U-USN-LARDNER"
              ],
              "note": "后卫驱逐队"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_6"
      },
      "special_rules": [
        {
          "id": "IBS-S-04-R1",
          "text": "岛屿放置：将萨沃岛小地图的X格对应放置在H6格。"
        },
        {
          "id": "IBS-S-04-R2",
          "text": "美军在第一回合无法发射鱼雷。"
        },
        {
          "id": "IBS-S-04-R3",
          "text": "因为存在岛屿，任何船只无法从地图南部离开，否则视为被击沉。"
        },
        {
          "id": "IBS-S-04-R4",
          "text": "在第一到第三回合，日军鱼雷攻击判定掷骰点数+1。"
        },
        {
          "id": "IBS-S-04-R5",
          "text": "区域存在的大片陆地影响美军重巡的8\"火炮火控，它们炮火强度减半（向上取整），但向东侧目标炮击则不受影响。"
        },
        {
          "id": "IBS-S-04-R6",
          "text": "日军可能受到增援。仅在第4回合开始时掷1枚骰子，如果掷到1或2，那么增援单位在移动阶段，以任意航速从G27至O27进入地图。“浜风”、“望月”、“三日月”按此顺序单纵队编队，划掉“浜风”的鱼雷再装填，因为它装载了额外的集装箱物资。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-04-R2",
          "kind": "turn_restriction",
          "sides": [
            "allies"
          ],
          "turns": [1],
          "actions": [
            "torpedo"
          ],
          "reason": "想定特例：美军在第一回合无法发射鱼雷"
        },
        {
          "id": "IBS-S-04-R4",
          "kind": "torpedo_roll_bonus",
          "sides": [
            "axis"
          ],
          "turns": [1, 2, 3],
          "bonus": 1
        },
        {
          "id": "IBS-S-04-R5",
          "kind": "firepower_multiplier",
          "sides": [
            "allies"
          ],
          "ship_types": [
            "CA"
          ],
          "caliber_min": 7.5,
          "caliber_max": 8.5,
          "factor": 0.5,
          "ceil": true,
          "unless_direction": "east",
          "note": "陆地影响美军重巡 8 吋火控：炮火强度减半向上取整；向东侧目标炮击不受影响"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-TAKANAMI",
          "name": "高波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "P16",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-高波.png"
        },
        {
          "id": "IBS-U-IJN-OYASHIO",
          "name": "亲潮",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "M19",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-亲潮.png"
        },
        {
          "id": "IBS-U-IJN-KUROSHIO",
          "name": "黑潮",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "L18",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-黑潮.png"
        },
        {
          "id": "IBS-U-IJN-KAGERO",
          "name": "阳炎",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K18",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-阳炎.png"
        },
        {
          "id": "IBS-U-IJN-MAKINAMI",
          "name": "卷波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "J17",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-卷波.png"
        },
        {
          "id": "IBS-U-IJN-NAGANAMI",
          "name": "长波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "I17",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-长波.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-KAWAKAZE",
          "name": "江风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H16",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-江风.png"
        },
        {
          "id": "IBS-U-IJN-SUZUKAZE",
          "name": "凉风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "G16",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-凉风.png"
        },
        {
          "id": "IBS-U-USN-FLETCHER",
          "name": "弗莱彻",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "V12",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-弗莱彻.png"
        },
        {
          "id": "IBS-U-USN-PERKINS",
          "name": "帕金斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "W13",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-帕金斯.png"
        },
        {
          "id": "IBS-U-USN-MAURY",
          "name": "莫里",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X13",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-莫里.png"
        },
        {
          "id": "IBS-U-USN-DRAYTON",
          "name": "德雷顿",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y14",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-德雷顿.png"
        },
        {
          "id": "IBS-U-USN-MINNEAPOLIS",
          "name": "明尼阿波里斯",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "AA15",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CA-明尼阿波里斯.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-NEW-ORLEANS",
          "name": "新奥尔良",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "BB15",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CA-新奥尔良.png"
        },
        {
          "id": "IBS-U-USN-PENSACOLA",
          "name": "彭萨科拉",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "CC16",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CA-彭萨科拉.png"
        },
        {
          "id": "IBS-U-USN-HONOLULU",
          "name": "火奴鲁鲁",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "DD16",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CL-火奴鲁鲁.png"
        },
        {
          "id": "IBS-U-USN-NORTHAMPTON",
          "name": "北安普敦",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "EE17",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CA-北安普敦.png"
        },
        {
          "id": "IBS-U-USN-LAMSON",
          "name": "拉姆森",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "FF17",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-拉姆森.png"
        },
        {
          "id": "IBS-U-USN-LARDNER",
          "name": "拉德纳",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG18",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-拉德纳.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 4,
          "roll": "1d6",
          "succeeds_on": [1, 2]
        },
        "arrival": {
          "turn": 4,
          "timing": "during_movement",
          "entry_hex_range": [
            "G27",
            "O27"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-IJN-HAMAKAZE",
            "name": "浜风",
            "side": "axis",
            "template": "dd-japanese-1942",
            "torpedo_reloads": 0,
            "asset": "日本-DD-浜风.png"
          },
          {
            "id": "IBS-U-IJN-MONCHIZUKI",
            "name": "望月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "asset": "日本-APD-望月.png"
          },
          {
            "id": "IBS-U-IJN-MIKAZUKI",
            "name": "三日月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "asset": "日本-APD-三日月.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 2,
        "allies_wins": 8,
        "draws": 0,
        "avg_turns": 6,
        "avg_sunk": {
          "axis": 1.6,
          "allies": 0.8
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-05": {
      "id": "IBS-S-05",
      "number": 5,
      "title": "圣乔治角海战",
      "date": "1943-11-25",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 5,
        "printed_page": 6,
        "status": "verified_source"
      },
      "turns": 10,
      "visibility": {
        "axis": 8,
        "allies": 7
      },
      "optional_rules": [
        "radar"
      ],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；一般模式与真实模式部署仍以 ships 初始位置和想定规则为权威。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-strike",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ONAMI",
                "IBS-U-IJN-MAKINAMI"
              ],
              "note": "圣乔治角夜战突击队（页面旗舰标注：大波——香川清登大佐）"
            }
          ],
          "allies": [
            {
              "id": "allies-desron23",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-CF-AUSBURNE",
                "IBS-U-USN-CLAXTON",
                "IBS-U-USN-DYSON",
                "IBS-U-USN-CONVERSE",
                "IBS-U-USN-SPENCE"
              ],
              "note": "第23驱逐舰中队（伯克上校“31节伯克”单纵）"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_10"
      },
      "special_rules": [
        {
          "id": "IBS-S-05-R1",
          "text": "日军在第一回合无法炮击和发射鱼雷。"
        },
        {
          "id": "IBS-S-05-R2",
          "text": "美军只能在雷达接触的范围发射鱼雷和炮击。"
        },
        {
          "id": "IBS-S-05-R3",
          "text": "双方都可以从地图北面离开，你也可以随时将它们从离开格正常移回地图，来保持彼此之间的关系。"
        },
        {
          "id": "IBS-S-05-R4",
          "text": "日军的三艘增援单位在第二回合达到。它们从地图HH9至HH16（也包括这两格）之间以任意航速进入地图。增援编队的次序是天雾、夕雾、卯月。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-05-R1",
          "kind": "turn_restriction",
          "sides": [
            "axis"
          ],
          "turns": [1],
          "actions": [
            "gunnery",
            "torpedo"
          ],
          "reason": "想定特例：日军在第一回合无法炮击和发射鱼雷"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-ONAMI",
          "name": "大波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "X15",
          "heading": 5,
          "speed": 4,
          "asset": "日本-DD-大波.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-MAKINAMI",
          "name": "卷波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "Y16",
          "heading": 5,
          "speed": 4,
          "asset": "日本-DD-卷波.png"
        },
        {
          "id": "IBS-U-USN-CF-AUSBURNE",
          "name": "查尔斯·奥斯本",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "N18",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-查尔斯·奥斯本.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-CLAXTON",
          "name": "克拉克斯顿",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "M18",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-克拉克斯顿.png"
        },
        {
          "id": "IBS-U-USN-DYSON",
          "name": "戴森",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "L18",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-戴森.png"
        },
        {
          "id": "IBS-U-USN-CONVERSE",
          "name": "康弗斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "K20",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-康弗斯.png"
        },
        {
          "id": "IBS-U-USN-SPENCE",
          "name": "斯彭斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "K19",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-斯彭斯.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 2,
          "roll": "1d6",
          "succeeds_on": [1, 2, 3, 4, 5, 6]
        },
        "arrival": {
          "turn": 2,
          "entry_hex_range": [
            "HH9",
            "HH16"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-IJN-AMAGIRI",
            "name": "天雾",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "asset": "日本-DD-天雾.png"
          },
          {
            "id": "IBS-U-IJN-YUGIRI",
            "name": "夕雾",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "asset": "日本-DD-夕雾.png"
          },
          {
            "id": "IBS-U-IJN-UZUKI-2",
            "name": "卯月(II)",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 5, 5],
            "asset": "日本-APD-卯月2.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 1,
        "allies_wins": 4,
        "draws": 5,
        "avg_turns": 10,
        "avg_sunk": {
          "axis": 0.4,
          "allies": 0
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-06": {
      "id": "IBS-S-06",
      "number": 6,
      "title": "第二次瓜达卡纳尔岛海战",
      "date": "1942-11-15",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 6,
        "printed_page": 7,
        "status": "verified_source"
      },
      "turns": 10,
      "visibility": {
        "axis": 21,
        "allies": 19
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；一般模式与真实模式部署仍以 ships 初始位置和想定规则为权威。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-close-screen",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-SENDAI",
                "IBS-U-IJN-SHIKINAMI",
                "IBS-U-IJN-URANAMI",
                "IBS-U-IJN-AYANAMI"
              ],
              "note": "近接警戒队（川内领头；页面未标旗舰，绫波单舰侧出）"
            },
            {
              "id": "axis-main-body",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-NAGARA",
                "IBS-U-IJN-SHIRAYUKI",
                "IBS-U-IJN-HATSUYUKI",
                "IBS-U-IJN-SAMIDARE",
                "IBS-U-IJN-INAZUMA"
              ],
              "note": "挺身攻击队本队（史实为阿部弘毅挺身攻击队；本想定援军含雾岛，无比叡）"
            }
          ],
          "allies": [
            {
              "id": "allies-van-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-WALKE",
                "IBS-U-USN-BENHAM",
                "IBS-U-USN-PRESTON",
                "IBS-U-USN-GWIN"
              ],
              "note": "前卫驱逐队（沃克上校）"
            },
            {
              "id": "allies-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-WASHINGTON",
                "IBS-U-USN-SOUTH-DAKOTA"
              ],
              "note": "战列舰纵列（李少将旗舰华盛顿）"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_10"
      },
      "special_rules": [
        {
          "id": "IBS-S-06-R1",
          "text": "岛屿放置：将萨沃岛小地图的X格对应放置在U6格。"
        },
        {
          "id": "IBS-S-06-R2",
          "text": "第三回合日军增援以任意航速从G1至L1进入地图。“爱宕”、“高雄”、“雾岛”、“朝云”、“照月”按此顺序单纵队编队。"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-SENDAI",
          "name": "川内",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "AA6",
          "heading": 3,
          "speed": 5,
          "asset": "日本-CL-川内.png"
        },
        {
          "id": "IBS-U-IJN-SHIKINAMI",
          "name": "敷波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "AA5",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-敷波.png"
        },
        {
          "id": "IBS-U-IJN-URANAMI",
          "name": "浦波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "AA4",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-浦波.png"
        },
        {
          "id": "IBS-U-IJN-AYANAMI",
          "name": "绫波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "M11",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-绫波.png"
        },
        {
          "id": "IBS-U-IJN-NAGARA",
          "name": "长良",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "H8",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-长良.png"
        },
        {
          "id": "IBS-U-IJN-SHIRAYUKI",
          "name": "白雪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "G8",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-白雪.png"
        },
        {
          "id": "IBS-U-IJN-HATSUYUKI",
          "name": "初雪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "F7",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-初雪.png"
        },
        {
          "id": "IBS-U-IJN-SAMIDARE",
          "name": "五月雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "F6",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-五月雨.png"
        },
        {
          "id": "IBS-U-IJN-INAZUMA",
          "name": "电",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "F5",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-电.png"
        },
        {
          "id": "IBS-U-USN-WALKE",
          "name": "沃克",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y20",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-沃克.png"
        },
        {
          "id": "IBS-U-USN-BENHAM",
          "name": "本汉姆",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z20",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-本汉姆.png"
        },
        {
          "id": "IBS-U-USN-PRESTON",
          "name": "普雷斯顿",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "AA21",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-普雷斯顿.png"
        },
        {
          "id": "IBS-U-USN-GWIN",
          "name": "葛文",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "BB21",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-葛文.png"
        },
        {
          "id": "IBS-U-USN-WASHINGTON",
          "name": "华盛顿",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "GG24",
          "heading": 5,
          "speed": 4,
          "asset": "美国-BB-华盛顿.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-SOUTH-DAKOTA",
          "name": "南达科塔",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "HH24",
          "heading": 5,
          "speed": 4,
          "asset": "美国-BB-南达科塔.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 3,
          "roll": "1d6",
          "succeeds_on": [1, 2, 3, 4, 5, 6]
        },
        "arrival": {
          "turn": 3,
          "entry_hex_range": [
            "G1",
            "L1"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-IJN-ATAGO",
            "name": "爱宕",
            "side": "axis",
            "template": "ca-japanese-1942",
            "speed_track": [6, 6, 5],
            "asset": "日本-CA-爱宕.png",
            "flagship": true
          },
          {
            "id": "IBS-U-IJN-TAKAO",
            "name": "高雄",
            "side": "axis",
            "template": "ca-japanese-1942",
            "speed_track": [6, 6, 5],
            "asset": "日本-CA-高雄.png"
          },
          {
            "id": "IBS-U-IJN-KIRISHIMA",
            "name": "雾岛",
            "side": "axis",
            "template": "ca-american-1942",
            "speed_track": [5, 5, 5],
            "asset": "日本-BB-雾岛.png"
          },
          {
            "id": "IBS-U-IJN-ASAGUMO",
            "name": "朝云",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 6, 5],
            "asset": "日本-DD-朝云.png"
          },
          {
            "id": "IBS-U-IJN-TERUZUKI",
            "name": "照月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "speed_track": [6, 5, 5],
            "asset": "日本-DD-照月.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 3,
        "allies_wins": 7,
        "draws": 0,
        "avg_turns": 10,
        "avg_sunk": {
          "axis": 1.3,
          "allies": 2
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-07": {
      "id": "IBS-S-07",
      "number": 7,
      "title": "所罗门群岛海战",
      "date": "1928-07-03",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 7,
        "printed_page": 8,
        "status": "verified_source"
      },
      "turns": 7,
      "visibility": {
        "axis": 14,
        "allies": 12
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；一般模式与真实模式部署仍以 ships 初始位置和想定规则为权威。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-battle-squadron",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-OWARI",
                "IBS-U-IJN-AKAGI",
                "IBS-U-IJN-AMAGI"
              ],
              "note": "第一战队（长浜少将旗舰尾张）"
            },
            {
              "id": "axis-screen",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-JINTSU-I",
                "IBS-U-IJN-ASAKAZE",
                "IBS-U-IJN-KAMIKAZE",
                "IBS-U-IJN-OITE",
                "IBS-U-IJN-UZUKI",
                "IBS-U-IJN-MUTSUKI",
                "IBS-U-IJN-TATSUTA"
              ],
              "note": "警戒队单纵"
            }
          ],
          "allies": [
            {
              "id": "allies-battle-squadron",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-UNNAMED-T01-R06",
                "IBS-U-USN-UNNAMED-T01-R08",
                "IBS-U-USN-UNNAMED-T01-R07"
              ],
              "note": "战列巡洋舰战队（雀曼中将旗舰列克星敦）"
            },
            {
              "id": "allies-screen-1",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-UNNAMED-T01-R22",
                "IBS-U-USN-DAHLGREN",
                "IBS-U-USN-PERRY",
                "IBS-U-USN-HULL-I",
                "IBS-U-USN-BAINBRIDGE"
              ],
              "note": "第一警戒队"
            },
            {
              "id": "allies-screen-2",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-MCDONOUGH",
                "IBS-U-USN-DECATUR",
                "IBS-U-USN-TRUXTON",
                "IBS-U-USN-FOX"
              ],
              "note": "第二警戒队"
            }
          ]
        }
      },
      "victory": {
        "kind": "bc_kill_comparison",
        "points_per_three_hull_lost": 1,
        "leader_margin": 5,
        "draw_if_margin_below": 5,
        "evaluated_at": "end_of_turn_7"
      },
      "special_rules": [
        {
          "id": "IBS-S-07-R1",
          "text": "第一回合双方都无法发射鱼雷。"
        },
        {
          "id": "IBS-S-07-R2",
          "text": "游戏第7回合结束时统计胜利分。每造成3点“船体”损失，计入1分。领先5分和以上，并且同时击沉战巡BC比对方多的玩家为胜利者。其他结果为平局。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-07-R1",
          "kind": "turn_restriction",
          "sides": [
            "axis",
            "allies"
          ],
          "turns": [1],
          "actions": [
            "torpedo"
          ],
          "reason": "想定特例：第一回合双方都无法发射鱼雷"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-OWARI",
          "name": "尾张",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "J9",
          "heading": 2,
          "speed": 4,
          "asset": "日本-BC-尾张.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-AKAGI",
          "name": "赤城",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "I9",
          "heading": 2,
          "speed": 4,
          "asset": "日本-BC-赤城.png"
        },
        {
          "id": "IBS-U-IJN-AMAGI",
          "name": "天城",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "H8",
          "heading": 2,
          "speed": 4,
          "asset": "日本-BC-天城.png"
        },
        {
          "id": "IBS-U-IJN-JINTSU-I",
          "name": "神通(I)",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "J13",
          "heading": 2,
          "speed": 4,
          "asset": "日本-CL-神通1.png"
        },
        {
          "id": "IBS-U-IJN-ASAKAZE",
          "name": "朝风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K13",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-朝风.png"
        },
        {
          "id": "IBS-U-IJN-KAMIKAZE",
          "name": "神风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H11",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-神风.png"
        },
        {
          "id": "IBS-U-IJN-OITE",
          "name": "追风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "G11",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-追风.png"
        },
        {
          "id": "IBS-U-IJN-UZUKI",
          "name": "卯月(I)",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "F10",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-卯月1.png"
        },
        {
          "id": "IBS-U-IJN-MUTSUKI",
          "name": "睦月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "E10",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-睦月.png"
        },
        {
          "id": "IBS-U-IJN-TATSUTA",
          "name": "龙田",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "F7",
          "heading": 2,
          "speed": 4,
          "asset": "日本-CL-龙田.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R22",
          "name": "孟菲斯",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "W17",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-孟菲斯.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R06",
          "name": "列克星敦",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "Y18",
          "heading": 4,
          "speed": 4,
          "asset": "美国-BC-列克星敦.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R08",
          "name": "宪法",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "Z18",
          "heading": 4,
          "speed": 4,
          "asset": "美国-BC-宪法.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R07",
          "name": "合众国",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "AA19",
          "heading": 4,
          "speed": 4,
          "asset": "美国-BC-合众国.png"
        },
        {
          "id": "IBS-U-USN-DAHLGREN",
          "name": "达尔格伦",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "V19",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-达尔格伦.png"
        },
        {
          "id": "IBS-U-USN-PERRY",
          "name": "佩里",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "W20",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-佩里.png"
        },
        {
          "id": "IBS-U-USN-HULL-I",
          "name": "赫尔(I)",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X20",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-赫尔1.png"
        },
        {
          "id": "IBS-U-USN-BAINBRIDGE",
          "name": "班布里奇",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y21",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-班布里奇.png"
        },
        {
          "id": "IBS-U-USN-MCDONOUGH",
          "name": "麦克多诺",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y15",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-麦克多诺.png"
        },
        {
          "id": "IBS-U-USN-DECATUR",
          "name": "迪凯特",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z15",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-迪凯特.png"
        },
        {
          "id": "IBS-U-USN-TRUXTON",
          "name": "特鲁斯顿",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "AA16",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-特鲁斯顿.png"
        },
        {
          "id": "IBS-U-USN-FOX",
          "name": "福克斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "BB16",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-福克斯.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 0,
        "allies_wins": 1,
        "draws": 9,
        "avg_turns": 7,
        "avg_sunk": {
          "axis": 2,
          "allies": 3.2
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-08": {
      "id": "IBS-S-08",
      "number": 8,
      "title": "科隆班加拉岛海战",
      "date": "1943-07-13",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 8,
        "printed_page": 9,
        "status": "verified_source"
      },
      "turns": 15,
      "visibility": {
        "axis": 19,
        "allies": 17
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；一般模式与真实模式部署仍以 ships 初始位置和想定规则为权威。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-strike-column",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-MIKAZUKI",
                "IBS-U-IJN-JINTSU-I",
                "IBS-U-IJN-YUKIKAZE",
                "IBS-U-IJN-HAMAKAZE",
                "IBS-U-IJN-KIYONAMI",
                "IBS-U-IJN-YUGURE"
              ],
              "note": "警戒队单纵（伊崎逸二少将旗舰神通）"
            }
          ],
          "allies": [
            {
              "id": "allies-van-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-NICHOLAS",
                "IBS-U-USN-OBANNON",
                "IBS-U-USN-TAYLOR",
                "IBS-U-USN-RADFORD",
                "IBS-U-USN-JENKINS"
              ],
              "note": "前卫驱逐队"
            },
            {
              "id": "allies-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-HONOLULU",
                "IBS-U-RN-UNNAMED-T05-R01",
                "IBS-U-USN-ST-LOUIS"
              ],
              "note": "巡洋舰纵列（安斯沃思少将旗舰火奴鲁鲁）"
            },
            {
              "id": "allies-rear-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-RALPH-TALBOT",
                "IBS-U-USN-BUCHANAN",
                "IBS-U-USN-GWIN",
                "IBS-U-USN-MAURY",
                "IBS-U-USN-WOODWORTH"
              ],
              "note": "后卫驱逐队"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_7"
      },
      "special_rules": [
        {
          "id": "IBS-S-08-R1",
          "text": "将萨沃岛小地图的Y格对应放置在B26格。"
        },
        {
          "id": "IBS-S-08-R2",
          "text": "将暴风雨标记放置在L5、M4、M6和O5。这些格和其相邻格立刻被暴雨影响。"
        },
        {
          "id": "IBS-S-08-R3",
          "text": "日军可能受到增援。仅在第4回合开始时掷1枚骰子，如果掷到1，那么增援单位在移动阶段开始前，以任意航速全部放置在E17至U27的格子。"
        },
        {
          "id": "IBS-S-08-R4",
          "text": "划掉所有增援单位的鱼雷再装填，因为它装载了额外的地面部队和物资。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-08-R2",
          "kind": "storm_markers",
          "hexes": [
            "L5",
            "M4",
            "M6",
            "O5"
          ],
          "note": "这些格与其相邻格立刻被暴雨影响（引擎按飑区规则判定）"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-MIKAZUKI",
          "name": "三日月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "F7",
          "heading": 2,
          "speed": 5,
          "asset": "日本-APD-三日月.png"
        },
        {
          "id": "IBS-U-IJN-JINTSU-I",
          "name": "神通(I)",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "E7",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-神通1.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-YUKIKAZE",
          "name": "雪风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "D6",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-雪风.png"
        },
        {
          "id": "IBS-U-IJN-HAMAKAZE",
          "name": "浜风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "C6",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-浜风.png"
        },
        {
          "id": "IBS-U-IJN-KIYONAMI",
          "name": "清波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "B5",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-清波.png"
        },
        {
          "id": "IBS-U-IJN-YUGURE",
          "name": "夕暮",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "A5",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-夕暮.png"
        },
        {
          "id": "IBS-U-USN-NICHOLAS",
          "name": "尼古拉斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "V16",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-尼古拉斯.png"
        },
        {
          "id": "IBS-U-USN-OBANNON",
          "name": "奥班农",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "W16",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-奥班农.png"
        },
        {
          "id": "IBS-U-USN-TAYLOR",
          "name": "泰勒",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X15",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-泰勒.png"
        },
        {
          "id": "IBS-U-USN-RADFORD",
          "name": "雷德福德",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y15",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-雷德福德.png"
        },
        {
          "id": "IBS-U-USN-JENKINS",
          "name": "詹金斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z14",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-詹金斯.png"
        },
        {
          "id": "IBS-U-USN-HONOLULU",
          "name": "火奴鲁鲁",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "AA14",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-火奴鲁鲁.png",
          "flagship": true
        },
        {
          "id": "IBS-U-RN-UNNAMED-T05-R01",
          "name": "利安德",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "BB14",
          "heading": 4,
          "speed": 4,
          "asset": "新西兰-CL-利安德.png"
        },
        {
          "id": "IBS-U-USN-ST-LOUIS",
          "name": "圣路易斯",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "BB13",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-圣路易斯.png"
        },
        {
          "id": "IBS-U-USN-RALPH-TALBOT",
          "name": "拉尔夫·托尔伯特",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "CC13",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-拉尔夫·托尔伯特.png"
        },
        {
          "id": "IBS-U-USN-BUCHANAN",
          "name": "布坎南",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "DD12",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-布坎南.png"
        },
        {
          "id": "IBS-U-USN-GWIN",
          "name": "葛文",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "EE12",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-葛文.png"
        },
        {
          "id": "IBS-U-USN-MAURY",
          "name": "莫里",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "FF11",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-莫里.png"
        },
        {
          "id": "IBS-U-USN-WOODWORTH",
          "name": "伍德沃斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG11",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-伍德沃斯.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 4,
          "roll": "1d6",
          "succeeds_on": [1]
        },
        "arrival": {
          "turn": 4,
          "timing": "before_movement_planning",
          "entry_hex_range": [
            "E17",
            "U27"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-IJN-SATSUKI",
            "name": "皋月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "torpedo_reloads": 0,
            "asset": "日本-APD-皋月.png"
          },
          {
            "id": "IBS-U-IJN-MINAZUKI",
            "name": "水无月",
            "side": "axis",
            "template": "dd-japanese-1942",
            "torpedo_reloads": 0,
            "asset": "日本-APD-水无月.png"
          },
          {
            "id": "IBS-U-IJN-XIFENG",
            "name": "夕风",
            "side": "axis",
            "template": "dd-japanese-1942",
            "torpedo_reloads": 0,
            "asset": "日本-APD-夕凪.png"
          },
          {
            "id": "IBS-U-IJN-MATSU-KAZE",
            "name": "松风",
            "side": "axis",
            "template": "dd-japanese-1942",
            "torpedo_reloads": 0,
            "asset": "日本-APD-松风.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 0,
        "allies_wins": 0,
        "draws": 10,
        "avg_turns": 1,
        "avg_sunk": {
          "axis": 0,
          "allies": 0
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-09": {
      "id": "IBS-S-09",
      "number": 9,
      "title": "第一次瓜达卡纳尔岛海战",
      "date": "1942-11-13",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 9,
        "printed_page": 10,
        "status": "verified_source"
      },
      "turns": 6,
      "visibility": {
        "axis": 10,
        "allies": 8
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；部署权威仍是 ships 初始位置与想定规则。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-vanguard-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-YUDACHI",
                "IBS-U-IJN-HARUSAME"
              ],
              "note": "前卫扫讨队（夕立/春雨）"
            },
            {
              "id": "axis-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-HIEI",
                "IBS-U-IJN-KIRISHIMA"
              ],
              "note": "挺身攻击队战列纵队（阿部弘毅中将旗舰比叡）"
            },
            {
              "id": "axis-screen",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-NAGARA",
                "IBS-U-IJN-IKAZUCHI",
                "IBS-U-IJN-AKATSUKI",
                "IBS-U-IJN-INAZUMA",
                "IBS-U-IJN-YUKIKAZE",
                "IBS-U-IJN-AMATSU-KAZE",
                "IBS-U-IJN-TERUZUKI"
              ],
              "note": "直卫警戒列（长良领头）"
            },
            {
              "id": "axis-rear-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ASAGUMO",
                "IBS-U-IJN-MURASAME",
                "IBS-U-IJN-SAMIDARE"
              ],
              "note": "后卫驱逐队"
            }
          ],
          "allies": [
            {
              "id": "allies-van-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-CUSHING",
                "IBS-U-USN-LAFFEY",
                "IBS-U-USN-STERETT",
                "IBS-U-USN-OBANNON"
              ],
              "note": "前卫驱逐队（库欣上校）"
            },
            {
              "id": "allies-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-UNNAMED-T01-R23",
                "IBS-U-USN-SAN-FRANCISCO",
                "IBS-U-USN-UNNAMED-T01-R20",
                "IBS-U-USN-HELENA",
                "IBS-U-USN-UNNAMED-T01-R24"
              ],
              "note": "巡洋舰纵列（卡拉汉少将旗舰旧金山；亚特兰大队首）"
            },
            {
              "id": "allies-rear-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-AARON-WARD",
                "IBS-U-USN-BARTON",
                "IBS-U-USN-MONSSEN",
                "IBS-U-USN-FLETCHER"
              ],
              "note": "后卫驱逐队"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_6"
      },
      "special_rules": [
        {
          "id": "IBS-S-09-R1",
          "text": "瓜达卡纳尔岛在地图东侧外，萨沃岛在地图东北侧外（背景情况，无需放置）。"
        },
        {
          "id": "IBS-S-09-R2",
          "text": "双方在第1回合都不能发射鱼雷。"
        },
        {
          "id": "IBS-S-09-R3",
          "text": "日军战列舰BB在第1和第2回合时，任何炮击都无法穿透装甲。因为他们正准备向亨德森机场炮击高爆弹。"
        },
        {
          "id": "IBS-S-09-R4",
          "text": "旧金山的舰尾主炮于当天早些时候被炸毁，需要先划掉。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-09-R2",
          "kind": "turn_restriction",
          "sides": [
            "axis",
            "allies"
          ],
          "turns": [1],
          "actions": [
            "torpedo"
          ],
          "reason": "想定特例：双方在第 1 回合都不能发射鱼雷"
        },
        {
          "id": "IBS-S-09-R3",
          "kind": "penetration_block",
          "sides": [
            "axis"
          ],
          "turns": [1, 2],
          "ship_types": [
            "BB"
          ],
          "note": "日军 BB 第 1-2 回合装高爆弹准备炮击机场，任何炮击都无法穿透装甲"
        },
        {
          "id": "IBS-S-09-R4",
          "kind": "setup_modification",
          "ship_id": "IBS-U-USN-SAN-FRANCISCO",
          "remove_mounts": {
            "kind": "primary",
            "position": "stern"
          },
          "note": "旧金山的舰尾主炮于当天早些时候被炸毁"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-YUDACHI",
          "name": "夕立",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "S12",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-夕立.png"
        },
        {
          "id": "IBS-U-IJN-HARUSAME",
          "name": "春雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "R11",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-春雨.png"
        },
        {
          "id": "IBS-U-IJN-NAGARA",
          "name": "长良",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "O10",
          "heading": 2,
          "speed": 3,
          "asset": "日本-CL-长良.png"
        },
        {
          "id": "IBS-U-IJN-INAZUMA",
          "name": "电",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K12",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-电.png"
        },
        {
          "id": "IBS-U-IJN-AKATSUKI",
          "name": "晓",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K11",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-晓.png"
        },
        {
          "id": "IBS-U-IJN-IKAZUCHI",
          "name": "雷",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K10",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-雷.png"
        },
        {
          "id": "IBS-U-IJN-HIEI",
          "name": "比叡",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "K8",
          "heading": 2,
          "speed": 3,
          "asset": "日本-BB-比叡.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-KIRISHIMA",
          "name": "雾岛",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "I7",
          "heading": 2,
          "speed": 3,
          "asset": "日本-BB-雾岛.png"
        },
        {
          "id": "IBS-U-IJN-YUKIKAZE",
          "name": "雪风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "M7",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-雪风.png"
        },
        {
          "id": "IBS-U-IJN-AMATSU-KAZE",
          "name": "天津风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "L6",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-天津风.png"
        },
        {
          "id": "IBS-U-IJN-TERUZUKI",
          "name": "照月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K6",
          "heading": 2,
          "speed": 3,
          "asset": "日本-DD-照月.png"
        },
        {
          "id": "IBS-U-IJN-ASAGUMO",
          "name": "朝云",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "I4",
          "heading": 1,
          "speed": 3,
          "asset": "日本-DD-朝云.png"
        },
        {
          "id": "IBS-U-IJN-MURASAME",
          "name": "村雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "H4",
          "heading": 1,
          "speed": 3,
          "asset": "日本-DD-村雨.png"
        },
        {
          "id": "IBS-U-IJN-SAMIDARE",
          "name": "五月雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "G5",
          "heading": 1,
          "speed": 3,
          "asset": "日本-DD-五月雨.png"
        },
        {
          "id": "IBS-U-USN-CUSHING",
          "name": "库欣",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "U17",
          "heading": 6,
          "speed": 4,
          "asset": "美国-DD-库欣.png"
        },
        {
          "id": "IBS-U-USN-LAFFEY",
          "name": "拉菲",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "U18",
          "heading": 6,
          "speed": 4,
          "asset": "美国-DD-拉菲.png"
        },
        {
          "id": "IBS-U-USN-STERETT",
          "name": "史特雷特",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "U19",
          "heading": 6,
          "speed": 4,
          "asset": "美国-DD-史特雷特.png"
        },
        {
          "id": "IBS-U-USN-OBANNON",
          "name": "奥班农",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "U20",
          "heading": 6,
          "speed": 4,
          "asset": "美国-DD-奥班农.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R23",
          "name": "亚特兰大",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "U21",
          "heading": 6,
          "speed": 4,
          "asset": "美国-CL-亚特兰大.png"
        },
        {
          "id": "IBS-U-USN-SAN-FRANCISCO",
          "name": "旧金山",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "U22",
          "heading": 6,
          "speed": 4,
          "asset": "美国-CA-旧金山.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R20",
          "name": "波特兰",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "U23",
          "heading": 6,
          "speed": 4,
          "asset": "美国-CA-波特兰.png"
        },
        {
          "id": "IBS-U-USN-HELENA",
          "name": "海伦娜",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "V23",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CL-海伦娜.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R24",
          "name": "朱诺",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "W24",
          "heading": 5,
          "speed": 4,
          "asset": "美国-CL-朱诺.png"
        },
        {
          "id": "IBS-U-USN-AARON-WARD",
          "name": "亚伦沃德",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X24",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-亚伦沃德.png"
        },
        {
          "id": "IBS-U-USN-BARTON",
          "name": "巴顿",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Y25",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-巴顿.png"
        },
        {
          "id": "IBS-U-USN-MONSSEN",
          "name": "蒙森",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z25",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-蒙森.png"
        },
        {
          "id": "IBS-U-USN-FLETCHER",
          "name": "弗莱彻",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "AA26",
          "heading": 5,
          "speed": 4,
          "asset": "美国-DD-弗莱彻.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 0,
        "allies_wins": 0,
        "draws": 10,
        "avg_turns": 1,
        "avg_sunk": {
          "axis": 0,
          "allies": 0
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-10": {
      "id": "IBS-S-10",
      "number": 10,
      "title": "萨沃岛海战",
      "date": "1942-08-09",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 10,
        "printed_page": 11,
        "status": "verified_source"
      },
      "turns": 30,
      "visibility": {
        "axis": 16,
        "allies": 8
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "initial_phase": "gunnery",
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；部署权威仍是 ships 初始位置与想定规则。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-cruiser-column",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-CHOKAI",
                "IBS-U-IJN-AOBA",
                "IBS-U-IJN-KAKO-I",
                "IBS-U-IJN-KINUGASA"
              ],
              "note": "外南洋巡逻部队主力单纵（三川军一少将旗舰鸟海）"
            },
            {
              "id": "axis-following",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-FURUTAKA",
                "IBS-U-IJN-TENRYU",
                "IBS-U-IJN-YUBARI",
                "IBS-U-IJN-XIFENG"
              ],
              "note": "后续追击队（按R1跟随衣笠）"
            }
          ],
          "allies": [
            {
              "id": "allies-southern-force",
              "role": "line_ahead",
              "ships": [
                "IBS-U-RAN-CANBERRA",
                "IBS-U-USN-UNNAMED-T01-R12",
                "IBS-U-USN-PATTERSON",
                "IBS-U-USN-BAGLEY",
                "IBS-U-USN-JARVIS"
              ],
              "note": "南方舰队（克拉奇利少将旗舰澳大利亚在增援）"
            },
            {
              "id": "allies-northern-force",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-VINCENNES",
                "IBS-U-USN-QUINCY",
                "IBS-U-USN-ASTORIA",
                "IBS-U-USN-WILSON",
                "IBS-U-USN-HELM"
              ],
              "note": "北方舰队"
            }
          ]
        }
      },
      "victory": {
        "kind": "score_threshold_tiers",
        "tactical_margin": 16,
        "decisive_margin": 50
      },
      "special_rules": [
        {
          "id": "IBS-S-10-R1",
          "text": "“天龙”，“夕张” & “夕凪” 排成一列依次跟随“衣笠”（领头），这三艘舰船到达时每艘船占据一个格子。"
        },
        {
          "id": "IBS-S-10-R2",
          "text": "将萨沃岛小地图的X格对应放置在A20格。"
        },
        {
          "id": "IBS-S-10-R3",
          "text": "第1回合时，日军16格，盟军8格。第2回合时，盟军提高到10格。第3回合开始盟军提高到12格。"
        },
        {
          "id": "IBS-S-10-R4",
          "text": "无限回合，当所有日军单位从地图A27-HH27离开地图时游戏结束。"
        },
        {
          "id": "IBS-S-10-R5",
          "text": "第1回合从炮击执行阶段开始，移动已经结束。只有日军在第1回合可以炮击。"
        },
        {
          "id": "IBS-S-10-R6",
          "text": "在第1回合开始，唯一警戒状态的是盟军南方编队，其他所有盟军单位都是未警戒状态。"
        },
        {
          "id": "IBS-S-10-R7",
          "text": "未警戒的单位只能保持原有方向和航速直行。"
        },
        {
          "id": "IBS-S-10-R8",
          "text": "警戒状态的单位第一回合无法炮击，但第二回合可以正常炮击。“堪培拉”，“芝加哥”，“巴格莱” 和 “帕特森” 四艘单位第1回合无法炮击，并且每回合航速只能提升1MF。"
        },
        {
          "id": "IBS-S-10-R9",
          "text": "当单位达成下列条件之一时，会转换成警戒状态：1，被炮击一次，无论是否被命中。2，被鱼雷命中一次。3，敌舰在可视范围内。"
        },
        {
          "id": "IBS-S-10-R10",
          "text": "第3回合开始，全部单位自动转换成警戒状态。"
        },
        {
          "id": "IBS-S-10-R11",
          "text": "在第一回合的炮击执行阶段前，日军可以在地图上放置一枚（飞机投放）的闪光弹。"
        },
        {
          "id": "IBS-S-10-R12",
          "text": "日军单位可以从HH1至HH16格离开地图，每离开一艘单位日军获得1分。"
        },
        {
          "id": "IBS-S-10-R13",
          "text": "离开地图前，每消耗1点鱼雷值获得4分。"
        },
        {
          "id": "IBS-S-10-R14",
          "text": "离开地图的单位可以在下回合从离开格的3格范围内返回地图。"
        },
        {
          "id": "IBS-S-10-R15",
          "text": "如果日军比盟军多16分，日军获得战术胜利。"
        },
        {
          "id": "IBS-S-10-R16",
          "text": "如果日军比盟军多50分，日军获得决定性胜利。"
        },
        {
          "id": "IBS-S-10-R17",
          "text": "如果分数差小于16分，盟军获得战术胜利。"
        },
        {
          "id": "IBS-S-10-R18",
          "text": "如果击沉3艘日军重巡，且盟军分数多，则盟军获得决定性胜利。"
        },
        {
          "id": "IBS-S-10-R19",
          "text": "其他情况为平局。"
        },
        {
          "id": "IBS-S-10-R20",
          "text": "盟军玩家可能获得增援。第2回合开始，在日军移动阶段之前，掷2枚骰子，如果点数之和与下面表格对应的结果出现未上场的增援单位，将他们依次以警戒状态进入地图。盟军后续每回合都掷骰判定增援。骰点表：2=澳大利亚、东方部队、拉尔夫·托尔伯特；3=澳大利亚、东方部队、布鲁；4=澳大利亚、东方部队、布鲁；5-9=没有新部队转移或加入；10=澳大利亚；11=澳大利亚、拉尔夫·托尔伯特；12=拉尔夫·托尔伯特 & 布鲁。"
        },
        {
          "id": "IBS-S-10-R21",
          "text": "“澳大利亚”从地图HH22-HH27格进入地图（包含这两格），“拉尔夫·托尔伯特”从A1-A8进入地图（包含这两格），“布鲁”从A21-A27进入地图（包含这两格），东方编队从HH3-HH21进入地图（包含这两格）。上述单位可以以任何航速进入地图，东方编队以任意单位领头，单纵队进入地图。"
        },
        {
          "id": "IBS-S-10-R22",
          "text": "如果日军单位离开地图，图拉吉护航编队可以进场。进场位置是离开地图的日军单位离开格的5格范围内，日军单位离开地图的2个回合后，图拉吉护航编队以任意航速进入。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-10-R3",
          "kind": "visibility_schedule",
          "side": "allies",
          "from_turn": {
            "1": 8,
            "2": 10,
            "3": 12
          }
        },
        {
          "id": "IBS-S-10-R5",
          "kind": "turn_restriction",
          "sides": [
            "allies"
          ],
          "turns": [1],
          "actions": [
            "gunnery"
          ],
          "reason": "想定特例：只有日军在第 1 回合可以炮击"
        },
        {
          "id": "IBS-S-10-R6",
          "kind": "alert_states",
          "sides": [
            "allies"
          ],
          "all_alerted_turn": 3,
          "initial": {
            "ships": [
              "IBS-U-RAN-CANBERRA",
              "IBS-U-USN-UNNAMED-T01-R12",
              "IBS-U-USN-PATTERSON",
              "IBS-U-USN-BAGLEY",
              "IBS-U-USN-JARVIS"
            ]
          },
          "speed_cap_ships": [
            "IBS-U-RAN-CANBERRA",
            "IBS-U-USN-UNNAMED-T01-R12",
            "IBS-U-USN-PATTERSON",
            "IBS-U-USN-BAGLEY"
          ],
          "note": "南方编队初始警戒；未警戒单位只能原向原速直行（R7）；4 舰每回合最多提速 1MF（R8）；被炮击/被雷命中/敌舰可视转警戒（R9）；第 3 回合全体警戒（R10）"
        },
        {
          "id": "IBS-S-10-R13",
          "kind": "torpedo_expenditure_points",
          "points_per_torpedo": 4,
          "note": "每消耗 1 点鱼雷值日军得 4 分（R13）；离场计分/返回见 R12/R14 文本（离场机制引擎暂未实现）"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-CHOKAI",
          "name": "鸟海",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "H23",
          "heading": 1,
          "speed": 5,
          "asset": "日本-CA-鸟海.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-AOBA",
          "name": "青叶",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "F24",
          "heading": 1,
          "speed": 5,
          "asset": "日本-CA-青叶.png"
        },
        {
          "id": "IBS-U-IJN-KAKO-I",
          "name": "加古(I)",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "D25",
          "heading": 1,
          "speed": 5,
          "asset": "日本-CA-加古1.png"
        },
        {
          "id": "IBS-U-IJN-KINUGASA",
          "name": "衣笠",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "B26",
          "heading": 1,
          "speed": 5,
          "asset": "日本-CA-衣笠.png"
        },
        {
          "id": "IBS-U-IJN-FURUTAKA",
          "name": "古鹰",
          "side": "axis",
          "template": "ca-japanese-1942",
          "asset": "日本-CA-古鹰.png"
        },
        {
          "id": "IBS-U-IJN-TENRYU",
          "name": "天龙",
          "side": "axis",
          "template": "cl-american-1942",
          "asset": "日本-CL-天龙.png"
        },
        {
          "id": "IBS-U-IJN-YUBARI",
          "name": "夕张",
          "side": "axis",
          "template": "cl-american-1942",
          "asset": "日本-CL-夕张.png"
        },
        {
          "id": "IBS-U-IJN-XIFENG",
          "name": "夕风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "asset": "日本-APD-夕凪.png"
        },
        {
          "id": "IBS-U-RAN-CANBERRA",
          "name": "堪培拉",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "P24",
          "heading": 5,
          "speed": 2,
          "asset": "澳大利亚-CA-堪培拉.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R12",
          "name": "芝加哥",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "Q25",
          "heading": 5,
          "speed": 2,
          "asset": "美国-CA-芝加哥.png"
        },
        {
          "id": "IBS-U-USN-PATTERSON",
          "name": "帕特森",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "N25",
          "heading": 5,
          "speed": 2,
          "asset": "美国-DD-帕特森.png"
        },
        {
          "id": "IBS-U-USN-BAGLEY",
          "name": "巴格莱",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "P22",
          "heading": 5,
          "speed": 2,
          "asset": "美国-DD-巴格莱.png"
        },
        {
          "id": "IBS-U-USN-JARVIS",
          "name": "贾维斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "J16",
          "heading": 4,
          "speed": 2,
          "asset": "美国-DD-贾维斯.png"
        },
        {
          "id": "IBS-U-USN-VINCENNES",
          "name": "文森斯",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "P8",
          "heading": 5,
          "speed": 2,
          "asset": "美国-CA-文森斯.png"
        },
        {
          "id": "IBS-U-USN-QUINCY",
          "name": "昆西",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "Q9",
          "heading": 5,
          "speed": 2,
          "asset": "美国-CA-昆西.png"
        },
        {
          "id": "IBS-U-USN-ASTORIA",
          "name": "阿斯托里亚",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "R9",
          "heading": 5,
          "speed": 2,
          "asset": "美国-CA-阿斯托里亚.png"
        },
        {
          "id": "IBS-U-USN-WILSON",
          "name": "威尔逊",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "P6",
          "heading": 5,
          "speed": 2,
          "asset": "美国-DD-威尔逊.png"
        },
        {
          "id": "IBS-U-USN-HELM",
          "name": "赫尔姆",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "N9",
          "heading": 4,
          "speed": 2,
          "asset": "美国-DD-赫尔姆.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 4,
        "allies_wins": 0,
        "draws": 6,
        "avg_turns": 14.7,
        "avg_sunk": {
          "axis": 0.5,
          "allies": 2.4
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-11": {
      "id": "IBS-S-11",
      "number": 11,
      "title": "奥古斯塔皇后湾海战",
      "date": "1943-11-02",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 12,
        "printed_page": 13,
        "status": "verified_source"
      },
      "turns": 9,
      "visibility": {
        "axis": 16,
        "allies": 12
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；部署权威仍是 ships 初始位置与想定规则。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-main",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-MYOKO",
                "IBS-U-IJN-HAGURO"
              ],
              "note": "主力队（大森仙太郎少将旗舰妙高）"
            },
            {
              "id": "axis-sendai-group",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-SENDAI",
                "IBS-U-IJN-SHIGURE",
                "IBS-U-IJN-SAMIDARE",
                "IBS-U-IJN-SHIRATSUYU"
              ],
              "note": "川内第一警戒队"
            },
            {
              "id": "axis-agano-group",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-AGANO",
                "IBS-U-IJN-NAGANAMI",
                "IBS-U-IJN-HATSU-KAZE",
                "IBS-U-IJN-WAKATSUKI"
              ],
              "note": "阿贺野第二警戒队（输送船团护卫）"
            }
          ],
          "allies": [
            {
              "id": "allies-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-UNNAMED-T01-R28",
                "IBS-U-USN-UNNAMED-T01-R26",
                "IBS-U-USN-UNNAMED-T01-R27",
                "IBS-U-USN-UNNAMED-T01-R29"
              ],
              "note": "巡洋舰纵列（梅里尔少将旗舰蒙彼利埃）"
            },
            {
              "id": "allies-van-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-CF-AUSBURNE",
                "IBS-U-USN-DYSON",
                "IBS-U-USN-STANLY",
                "IBS-U-USN-CLAXTON"
              ],
              "note": "前卫驱逐队（伯克上校）"
            },
            {
              "id": "allies-rear-dd",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-SPENCE",
                "IBS-U-USN-THATCHER",
                "IBS-U-USN-CONVERSE",
                "IBS-U-USN-FOOTE"
              ],
              "note": "后卫驱逐队"
            }
          ]
        }
      },
      "victory": {
        "kind": "vp_with_decisive_margin",
        "decisive_margin": 20,
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_9"
      },
      "special_rules": [
        {
          "id": "IBS-S-11-R1",
          "text": "9个回合，或所有日军单位离开地图。"
        },
        {
          "id": "IBS-S-11-R2",
          "text": "一架日军侦察机在战场内，双方所有移动命令写完之后，日军可以在地图上任意位置放置一枚照明弹。"
        },
        {
          "id": "IBS-S-11-R3",
          "text": "由于之前的空袭行动，羽黑舰在划掉1点船体，且航速减少至6-5-5的状态进场。"
        },
        {
          "id": "IBS-S-11-R4",
          "text": "如果差值达到20分，视为决定性胜利。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-11-R3",
          "kind": "setup_modification",
          "ship_id": "IBS-U-IJN-HAGURO",
          "hull_damage": 1,
          "speed_damage_track": [
            [6, 5, 4, 3, 2, 1],
            [5, 4, 3, 2, 1],
            [5, 4, 3, 2, 1]
          ]
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-MYOKO",
          "name": "妙高",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "G16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-妙高.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-HAGURO",
          "name": "羽黑",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "F15",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-羽黑.png"
        },
        {
          "id": "IBS-U-IJN-SENDAI",
          "name": "川内",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "M11",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-川内.png"
        },
        {
          "id": "IBS-U-IJN-SHIGURE",
          "name": "时雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "L10",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-时雨.png"
        },
        {
          "id": "IBS-U-IJN-SAMIDARE",
          "name": "五月雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K10",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-五月雨.png"
        },
        {
          "id": "IBS-U-IJN-SHIRATSUYU",
          "name": "白露",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "J9",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-白露.png"
        },
        {
          "id": "IBS-U-IJN-AGANO",
          "name": "阿贺野",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "D22",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-阿贺野.png"
        },
        {
          "id": "IBS-U-IJN-NAGANAMI",
          "name": "长波",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "C22",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-长波.png"
        },
        {
          "id": "IBS-U-IJN-HATSU-KAZE",
          "name": "初风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "B21",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-初风.png"
        },
        {
          "id": "IBS-U-IJN-WAKATSUKI",
          "name": "若月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "A21",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-若月.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R28",
          "name": "蒙彼利埃",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "EE14",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-蒙彼利埃.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R26",
          "name": "克利夫兰",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "EE15",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-克利夫兰.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R27",
          "name": "哥伦比亚",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "EE16",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-哥伦比亚.png"
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R29",
          "name": "丹弗",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "EE17",
          "heading": 4,
          "speed": 4,
          "asset": "美国-CL-丹佛.png"
        },
        {
          "id": "IBS-U-USN-CF-AUSBURNE",
          "name": "查尔斯·奥斯本",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "CC8",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-查尔斯·奥斯本.png"
        },
        {
          "id": "IBS-U-USN-DYSON",
          "name": "戴森",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "CC9",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-戴森.png"
        },
        {
          "id": "IBS-U-USN-STANLY",
          "name": "斯坦立",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "CC10",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-斯坦立.png"
        },
        {
          "id": "IBS-U-USN-CLAXTON",
          "name": "克拉克斯顿",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "CC11",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-克拉克斯顿.png"
        },
        {
          "id": "IBS-U-USN-SPENCE",
          "name": "斯彭斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG19",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-斯彭斯.png"
        },
        {
          "id": "IBS-U-USN-THATCHER",
          "name": "撒切尔",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG20",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-撒切尔.png"
        },
        {
          "id": "IBS-U-USN-CONVERSE",
          "name": "康弗斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG21",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-康弗斯.png"
        },
        {
          "id": "IBS-U-USN-FOOTE",
          "name": "福特",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG22",
          "heading": 4,
          "speed": 4,
          "asset": "美国-DD-福特.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 1,
        "allies_wins": 8,
        "draws": 1,
        "avg_turns": 9,
        "avg_sunk": {
          "axis": 2.7,
          "allies": 2.2
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-12": {
      "id": "IBS-S-12",
      "number": 12,
      "title": "布干维尔岛海战（第一战队出击！）",
      "date": "1928-03-03",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 13,
        "printed_page": 14,
        "status": "verified_source"
      },
      "turns": 9,
      "visibility": {
        "axis": 14,
        "allies": 12
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；部署权威仍是 ships 初始位置与想定规则。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-main-body",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-NAGATO",
                "IBS-U-IJN-MUTSU"
              ],
              "note": "第一战队（长门旗舰）"
            },
            {
              "id": "axis-screen",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-JINTSU-I",
                "IBS-U-IJN-KAMIKAZE",
                "IBS-U-IJN-OITE",
                "IBS-U-IJN-HATSUYUKI"
              ],
              "note": "警戒队"
            },
            {
              "id": "axis-van",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-KAKO-I"
              ],
              "note": "前卫（加古；不足 2 舰由引擎并入相邻纵队）"
            }
          ],
          "allies": [
            {
              "id": "allies-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-COLORADO",
                "IBS-U-USN-WEST-VIRGINIA"
              ],
              "note": "战列舰纵队"
            },
            {
              "id": "allies-screen-1",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-OMAHA",
                "IBS-U-USN-DAHLGREN",
                "IBS-U-USN-PERRY"
              ],
              "note": "第一警戒队"
            },
            {
              "id": "allies-screen-2",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-HULL-I",
                "IBS-U-USN-BAINBRIDGE"
              ],
              "note": "第二警戒队"
            }
          ]
        }
      },
      "victory": {
        "kind": "vp_with_bb_decisive_clause",
        "points_per_three_hull_lost": 1,
        "leader_margin": 4,
        "draw_if_margin_below": 4,
        "evaluated_at": "end_of_turn_9"
      },
      "special_rules": [
        {
          "id": "IBS-S-12-R1",
          "text": "双方都对第一次接触很震惊，双方第一回合都无法炮击和发射鱼雷。"
        },
        {
          "id": "IBS-S-12-R2",
          "text": "如果敌方损失1-2艘战列舰，而己方无战列舰损失，视为决定性胜利。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-12-R1",
          "kind": "turn_restriction",
          "sides": [
            "axis",
            "allies"
          ],
          "turns": [1],
          "actions": [
            "gunnery",
            "torpedo"
          ],
          "reason": "想定特例：双方第一回合都无法炮击和发射鱼雷"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-KAKO-I",
          "name": "加古(I)",
          "side": "axis",
          "template": "ca-japanese-1942",
          "position": "P9",
          "heading": 2,
          "speed": 4,
          "asset": "日本-CA-加古1.png"
        },
        {
          "id": "IBS-U-IJN-NAGATO",
          "name": "长门",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "N8",
          "heading": 2,
          "speed": 4,
          "asset": "日本-BB-长门.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-MUTSU",
          "name": "陆奥",
          "side": "axis",
          "template": "ca-american-1942",
          "position": "M8",
          "heading": 2,
          "speed": 4,
          "asset": "日本-BB-陆奥.png"
        },
        {
          "id": "IBS-U-IJN-JINTSU-I",
          "name": "神通(I)",
          "side": "axis",
          "template": "cl-american-1942",
          "position": "S8",
          "heading": 2,
          "speed": 4,
          "asset": "日本-CL-神通1.png"
        },
        {
          "id": "IBS-U-IJN-KAMIKAZE",
          "name": "神风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "R7",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-神风.png"
        },
        {
          "id": "IBS-U-IJN-OITE",
          "name": "追风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "Q7",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-追风.png"
        },
        {
          "id": "IBS-U-IJN-HATSUYUKI",
          "name": "初雪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "P6",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-初雪.png"
        },
        {
          "id": "IBS-U-USN-COLORADO",
          "name": "科罗拉多",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "Z19",
          "heading": 5,
          "speed": 3,
          "asset": "美国-BB-科罗拉多.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-WEST-VIRGINIA",
          "name": "西弗吉尼亚",
          "side": "allies",
          "template": "ca-american-1942",
          "position": "AA20",
          "heading": 5,
          "speed": 3,
          "asset": "美国-BB-西弗吉尼亚.png"
        },
        {
          "id": "IBS-U-USN-OMAHA",
          "name": "奥马哈",
          "side": "allies",
          "template": "cl-american-1942",
          "position": "V20",
          "heading": 5,
          "speed": 3,
          "asset": "美国-CL-奥马哈.png"
        },
        {
          "id": "IBS-U-USN-DAHLGREN",
          "name": "达尔格伦",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "W21",
          "heading": 5,
          "speed": 3,
          "asset": "美国-DD-达尔格伦.png"
        },
        {
          "id": "IBS-U-USN-PERRY",
          "name": "佩里",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "X21",
          "heading": 5,
          "speed": 3,
          "asset": "美国-DD-佩里.png"
        },
        {
          "id": "IBS-U-USN-HULL-I",
          "name": "赫尔(I)",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "AA17",
          "heading": 5,
          "speed": 3,
          "asset": "美国-DD-赫尔1.png"
        },
        {
          "id": "IBS-U-USN-BAINBRIDGE",
          "name": "班布里奇",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "BB17",
          "heading": 5,
          "speed": 3,
          "asset": "美国-DD-班布里奇.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 2,
        "allies_wins": 4,
        "draws": 4,
        "avg_turns": 9,
        "avg_sunk": {
          "axis": 1.1,
          "allies": 1
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-13": {
      "id": "IBS-S-13",
      "number": 13,
      "title": "韦拉拉韦拉岛海战",
      "date": "1943-10-06",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 14,
        "printed_page": 15,
        "status": "verified_source"
      },
      "turns": 11,
      "visibility": {
        "axis": 24,
        "allies": 20
      },
      "optional_rules": [
        "radar"
      ],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；部署权威仍是 ships 初始位置与想定规则。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-strike",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-AKIGUMO",
                "IBS-U-IJN-ISOKAZE",
                "IBS-U-IJN-KAZEKUMO",
                "IBS-U-IJN-YUGUMO"
              ],
              "note": "掩护突击队（伊集院松治大佐旗舰秋云）"
            },
            {
              "id": "axis-transport",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-SHIGURE",
                "IBS-U-IJN-SAMIDARE",
                "IBS-U-IJN-YUNAGI",
                "IBS-U-IJN-FUMIZUKI",
                "IBS-U-IJN-MATSU-KAZE"
              ],
              "note": "韦拉拉韦拉输送队（西村祥治少将旗舰时雨）"
            }
          ],
          "allies": [
            {
              "id": "allies-desdiv",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-SELFRIDGE",
                "IBS-U-USN-CHEVALIER",
                "IBS-U-USN-OBANNON"
              ],
              "note": "盟军驱逐单纵（赛尔弗里纪旗舰）"
            }
          ]
        }
      },
      "victory": {
        "kind": "dd_kill_comparison"
      },
      "special_rules": [
        {
          "id": "IBS-S-13-R1",
          "text": "所有盟军单位拥有雷达。"
        },
        {
          "id": "IBS-S-13-R2",
          "text": "盟军玩家在游戏开始前秘密写下一个格子编号，在L27-V27之间的。第2回合开始，盟军在回合开始时掷2枚骰子，如果点数和为10或11，则“拉尔夫·托尔伯特”、“泰勒”、“拉瓦利特”按次序单纵队以5-5-5的航速进入地图（之前写下的格子编号）。盟军玩家之后的每回合开始时都掷骰判定，直到第8回合开始时，增援自动进场。"
        },
        {
          "id": "IBS-S-13-R3",
          "text": "日军可以将增援的3艘APD排在五月雨之后的E3、E2、E1。如果这样的话，为了平衡，盟军增援掷骰的成功点数之和改为9-12。"
        },
        {
          "id": "IBS-S-13-R4",
          "text": "回合结束时，如果盟军击沉敌方3艘DD，己方只被击沉1艘DD或更少，则盟军战役级胜利。"
        },
        {
          "id": "IBS-S-13-R5",
          "text": "如果日军击沉敌方3艘DD，己方无任何DD被击沉，则日军战役级胜利。除此之外的结果为平局。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-13-R1",
          "kind": "setup_modification",
          "sides": [
            "allies"
          ],
          "radar": true
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-AKIGUMO",
          "name": "秋云",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "L12",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-秋云.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-ISOKAZE",
          "name": "矶风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "K13",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-矶风.png"
        },
        {
          "id": "IBS-U-IJN-KAZEKUMO",
          "name": "风云",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "J13",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-风云.png"
        },
        {
          "id": "IBS-U-IJN-YUGUMO",
          "name": "夕云",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "I14",
          "heading": 2,
          "speed": 4,
          "asset": "日本-DD-夕云.png"
        },
        {
          "id": "IBS-U-IJN-SHIGURE",
          "name": "时雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "E5",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-时雨.png"
        },
        {
          "id": "IBS-U-IJN-SAMIDARE",
          "name": "五月雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "E4",
          "heading": 3,
          "speed": 5,
          "asset": "日本-DD-五月雨.png"
        },
        {
          "id": "IBS-U-IJN-YUNAGI",
          "name": "夕凪",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "E3",
          "heading": 3,
          "speed": 5,
          "asset": "日本-APD-夕凪.png"
        },
        {
          "id": "IBS-U-IJN-FUMIZUKI",
          "name": "文月",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "E2",
          "heading": 3,
          "speed": 5,
          "asset": "日本-APD-文月.png"
        },
        {
          "id": "IBS-U-IJN-MATSU-KAZE",
          "name": "松风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "E1",
          "heading": 3,
          "speed": 5,
          "asset": "日本-APD-松风.png"
        },
        {
          "id": "IBS-U-USN-SELFRIDGE",
          "name": "赛尔弗里纪",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "Z7",
          "heading": 4,
          "speed": 5,
          "asset": "美国-DD-赛尔弗里纪.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-CHEVALIER",
          "name": "谢伐利埃",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "AA7",
          "heading": 4,
          "speed": 5,
          "asset": "美国-DD-谢伐利埃.png"
        },
        {
          "id": "IBS-U-USN-OBANNON",
          "name": "奥班农",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "BB6",
          "heading": 4,
          "speed": 5,
          "asset": "美国-DD-奥班农.png"
        }
      ],
      "reinforcements": {
        "trigger": {
          "turn": 7,
          "roll": "1d6",
          "succeeds_on": [1, 2, 3, 4, 5, 6]
        },
        "arrival": {
          "turn": 8,
          "entry_hex_range": [
            "L27",
            "V27"
          ],
          "speed": "any_legal"
        },
        "ships": [
          {
            "id": "IBS-U-USN-RALPH-TALBOT",
            "name": "拉尔夫·托尔伯特",
            "side": "allies",
            "template": "dd-american-1942",
            "speed_track": [5, 5, 5],
            "asset": "美国-DD-拉尔夫·托尔伯特.png"
          },
          {
            "id": "IBS-U-USN-TAYLOR",
            "name": "泰勒",
            "side": "allies",
            "template": "dd-american-1942",
            "speed_track": [5, 5, 5],
            "asset": "美国-DD-泰勒.png"
          },
          {
            "id": "IBS-U-USN-LA-VALLETTE",
            "name": "拉瓦利特",
            "side": "allies",
            "template": "dd-american-1942",
            "speed_track": [5, 5, 5],
            "asset": "美国-DD-拉瓦利特.png"
          }
        ]
      },
      "ai_stats": {
        "games": 10,
        "axis_wins": 1,
        "allies_wins": 1,
        "draws": 8,
        "avg_turns": 11,
        "avg_sunk": {
          "axis": 1.9,
          "allies": 2.5
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-14": {
      "id": "IBS-S-14",
      "number": 14,
      "title": "霍腊纽海战",
      "date": "1943-08-18",
      "status": "playable",
      "source": {
        "document": "scenario-book-zh.pdf",
        "pdf_page": 15,
        "printed_page": 16,
        "status": "verified_source"
      },
      "turns": 12,
      "visibility": {
        "axis": 27,
        "allies": 25
      },
      "optional_rules": [
        "radar"
      ],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 仅为真实模式直接开局的默认编队提案；部署权威仍是 ships 初始位置与想定规则。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-pair-1",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-SAZANAMI",
                "IBS-U-IJN-HAMAKAZE"
              ],
              "note": "第一组（涟旗舰）"
            },
            {
              "id": "axis-pair-2",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ISOKAZE",
                "IBS-U-IJN-SHIGURE"
              ],
              "note": "第二组"
            }
          ],
          "allies": [
            {
              "id": "allies-desdiv",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-NICHOLAS",
                "IBS-U-USN-OBANNON",
                "IBS-U-USN-TAYLOR",
                "IBS-U-USN-CHEVALIER"
              ],
              "note": "盟军驱逐纵队（尼古拉斯旗舰）"
            }
          ]
        }
      },
      "victory": {
        "kind": "margin_tiers",
        "tactical_margin": 3,
        "campaign_margin": 6
      },
      "special_rules": [
        {
          "id": "IBS-S-14-R1",
          "text": "所有盟军单位拥有雷达。南方为明亮的月光，所以任何向南方目标炮击的单位都可以获得火炮修正-2。"
        },
        {
          "id": "IBS-S-14-R2",
          "text": "除了驳船之外，任何船只都无法离开地图的南方边界。"
        },
        {
          "id": "IBS-S-14-R3",
          "text": "游戏开始时，战场中有一架日军水上侦察机，在第2回合时可以投放照明弹。（按照9.3的照明弹规则，在第1回合写下格子编号。）第4或第5回合时，日军还有一次写下照明弹位置的机会。"
        },
        {
          "id": "IBS-S-14-R4",
          "text": "日军在G17和H17的方向3还有两个假目标算子，他们只能以2-1-1的航速移动。参见假目标规则，日军玩家暗自用真假目标的方式区分开它们，视为两艘驳船小编队。"
        },
        {
          "id": "IBS-S-14-R5",
          "text": "驳船由两枚假目标算子表示，他们将努力活着从南方边界离开。"
        },
        {
          "id": "IBS-S-14-R6",
          "text": "美军驱逐舰只能在6格或更近距离向驳船单位炮击，必须集中炮击，无法分别炮击多个单位。然后掷2枚骰子，只有点数和为12时，视为击沉驳船。每个击沉的驳船美军获得2分。"
        },
        {
          "id": "IBS-S-14-R7",
          "text": "任何一方领先3分即为战术胜利。如果领先6分，则为战役级胜利。其他情况为平局。"
        }
      ],
      "special_rule_kinds": [
        {
          "id": "IBS-S-14-R1",
          "kind": "setup_modification",
          "sides": [
            "allies"
          ],
          "radar": true
        },
        {
          "id": "IBS-S-14-R1B",
          "kind": "gunnery_direction_modifier",
          "toward": "south",
          "modifier": -2,
          "note": "南方月光明亮：向南方目标炮击的单位获得火炮修正 -2"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-SAZANAMI",
          "name": "涟",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "O11",
          "heading": 5,
          "speed": 4,
          "asset": "日本-DD-涟.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-HAMAKAZE",
          "name": "浜风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "P11",
          "heading": 5,
          "speed": 4,
          "asset": "日本-DD-浜风.png"
        },
        {
          "id": "IBS-U-IJN-ISOKAZE",
          "name": "矶风",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "N7",
          "heading": 5,
          "speed": 4,
          "asset": "日本-DD-矶风.png"
        },
        {
          "id": "IBS-U-IJN-SHIGURE",
          "name": "时雨",
          "side": "axis",
          "template": "dd-japanese-1942",
          "position": "N6",
          "heading": 5,
          "speed": 4,
          "asset": "日本-DD-时雨.png"
        },
        {
          "id": "IBS-U-USN-NICHOLAS",
          "name": "尼古拉斯",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "EE24",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-尼古拉斯.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-OBANNON",
          "name": "奥班农",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "FF24",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-奥班农.png"
        },
        {
          "id": "IBS-U-USN-TAYLOR",
          "name": "泰勒",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "GG25",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-泰勒.png"
        },
        {
          "id": "IBS-U-USN-CHEVALIER",
          "name": "谢伐利埃",
          "side": "allies",
          "template": "dd-american-1942",
          "position": "HH25",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-谢伐利埃.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 3,
        "allies_wins": 6,
        "draws": 1,
        "avg_turns": 12,
        "avg_sunk": {
          "axis": 1.7,
          "allies": 1.1
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-EM-01": {
      "id": "IBS-S-EM-01",
      "number": "EM-01",
      "title": "第二次马里亚纳海战（内南洋水雷强袭战）",
      "date": "1944-06-21",
      "status": "playable",
      "source": {
        "document": "extensions/erma/scenario/second-battle-of-the-philippine-sea-zh.pdf",
        "pdf_pages": [1, 2],
        "status": "verified_source"
      },
      "turns": 12,
      "source_turns": 8,
      "turn_limit_authority": "user_requested_project_extension",
      "initial_phase": "gunnery",
      "visibility": {
        "axis": 15,
        "allies": 13
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "free_deployment",
        "first_player": "highest_1d6",
        "order": [
          "large_ships_alternating",
          "small_ships_alternating"
        ],
        "large_ship_types": [
          "BB",
          "BC",
          "CB"
        ],
        "small_ship_types": [
          "CA",
          "CL",
          "DD"
        ],
        "start_after_setup": {
          "turn": 1,
          "phase": "gunnery"
        },
        "zones": {
          "axis": {
            "from": "A14",
            "to": "Q1",
            "side": "northwest",
            "include_line": false
          },
          "allies": {
            "from": "R27",
            "to": "HH14",
            "side": "southeast",
            "include_line": false
          }
        },
        "engine_default_note": "合法的预置编队仅用于直接开局；自由部署约束仍以本节为权威数据。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ERMA-YAMATO",
                "IBS-U-IJN-ERMA-MUSASHI",
                "IBS-U-IJN-ERMA-SHINANO",
                "IBS-U-IJN-ERMA-AZUMA",
                "IBS-U-IJN-ERMA-ISHIKARI"
              ]
            },
            {
              "id": "axis-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ERMA-IBUKI",
                "IBS-U-IJN-ERMA-KURAMA",
                "IBS-U-IJN-ERMA-GOKASE"
              ]
            },
            {
              "id": "axis-destroyer-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ERMA-SHIMAKAZE",
                "IBS-U-IJN-ERMA-KAZEGUMO",
                "IBS-U-IJN-ERMA-NAGANAMI",
                "IBS-U-IJN-ERMA-MAKINAMI"
              ]
            }
          ],
          "allies": [
            {
              "id": "allies-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-ERMA-IOWA",
                "IBS-U-USN-ERMA-NEW-JERSEY",
                "IBS-U-USN-ERMA-MISSOURI",
                "IBS-U-USN-ERMA-WISCONSIN",
                "IBS-U-USN-ERMA-ALASKA",
                "IBS-U-USN-ERMA-GUAM"
              ]
            },
            {
              "id": "allies-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-ERMA-DES-MOINES",
                "IBS-U-USN-ERMA-SALEM",
                "IBS-U-USN-ERMA-WORCESTER"
              ]
            },
            {
              "id": "allies-destroyer-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-ERMA-ALLEN-M-SUMNER",
                "IBS-U-USN-ERMA-INGRAHAM",
                "IBS-U-USN-ERMA-COOPER"
              ]
            }
          ]
        }
      },
      "scenario_rules": [
        {
          "id": "IBS-S-EM-01-R1",
          "kind": "free_deployment",
          "source_page": 1
        },
        {
          "id": "IBS-S-EM-01-R2",
          "kind": "gunnery_hit_table_extension",
          "table": "erma-gunnery-hit-extension.csv",
          "source_page": 2
        },
        {
          "id": "IBS-S-EM-01-R3",
          "kind": "japanese_3_9_penetrates_as_3_inch",
          "source_page": 2
        },
        {
          "id": "IBS-S-EM-01-R4",
          "kind": "damage_points_victory",
          "margin": 25,
          "source_page": 2
        },
        {
          "id": "IBS-S-EM-01-R5",
          "kind": "user_extended_turn_limit",
          "turns": 12,
          "replaces_source_turn_limit": 8,
          "authority": "user_requested_project_extension"
        }
      ],
      "victory": {
        "kind": "erma_damage_points",
        "evaluated_at": "end_of_turn_12",
        "win_margin": 25,
        "scoring": {
          "hull_loss": {
            "per": 3,
            "points": 1
          },
          "battleship_fire_control_destroyed": 1,
          "battleship_radar_destroyed": 1,
          "battleship_primary_mount_destroyed": 1,
          "battleship_speed_loss": {
            "per": 2,
            "points": 1
          }
        }
      },
      "ships": [
        {
          "id": "IBS-U-IJN-ERMA-YAMATO",
          "name": "大和",
          "side": "axis",
          "position": "J3",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-大和-二马.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-ERMA-MUSASHI",
          "name": "武藏",
          "side": "axis",
          "position": "I3",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-武藏.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-SHINANO",
          "name": "信浓",
          "side": "axis",
          "position": "H2",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-信浓.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-AZUMA",
          "name": "吾妻",
          "side": "axis",
          "position": "G2",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CB-吾妻.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-ISHIKARI",
          "name": "石狩",
          "side": "axis",
          "position": "F1",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CB-石狩.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-IBUKI",
          "name": "伊吹",
          "side": "axis",
          "position": "G5",
          "heading": 2,
          "speed": 6,
          "asset": "日本-CA-伊吹.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-KURAMA",
          "name": "鞍马",
          "side": "axis",
          "position": "F4",
          "heading": 2,
          "speed": 6,
          "asset": "日本-CA-鞍马.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-GOKASE",
          "name": "五濑",
          "side": "axis",
          "position": "E4",
          "heading": 2,
          "speed": 6,
          "asset": "日本-CL-五濑.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-SHIMAKAZE",
          "name": "岛风",
          "side": "axis",
          "position": "D9",
          "heading": 2,
          "speed": 6,
          "asset": "日本-DD-岛风.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-KAZEGUMO",
          "name": "风云",
          "side": "axis",
          "position": "C9",
          "heading": 2,
          "speed": 6,
          "asset": "日本-DD-风云.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-NAGANAMI",
          "name": "长波",
          "side": "axis",
          "position": "B8",
          "heading": 2,
          "speed": 6,
          "asset": "日本-DD-长波.png"
        },
        {
          "id": "IBS-U-IJN-ERMA-MAKINAMI",
          "name": "卷波",
          "side": "axis",
          "position": "A8",
          "heading": 2,
          "speed": 6,
          "asset": "日本-DD-卷波.png"
        },
        {
          "id": "IBS-U-USN-ERMA-IOWA",
          "name": "衣阿华",
          "side": "allies",
          "position": "Y23",
          "heading": 5,
          "speed": 6,
          "asset": "美国-BB-衣阿华.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-ERMA-NEW-JERSEY",
          "name": "新泽西",
          "side": "allies",
          "position": "Z23",
          "heading": 5,
          "speed": 6,
          "asset": "美国-BB-新泽西.png"
        },
        {
          "id": "IBS-U-USN-ERMA-MISSOURI",
          "name": "密苏里",
          "side": "allies",
          "position": "AA24",
          "heading": 5,
          "speed": 6,
          "asset": "美国-BB-密苏里.png"
        },
        {
          "id": "IBS-U-USN-ERMA-WISCONSIN",
          "name": "威斯康星",
          "side": "allies",
          "position": "BB24",
          "heading": 5,
          "speed": 6,
          "asset": "美国-BB-威斯康星.png"
        },
        {
          "id": "IBS-U-USN-ERMA-ALASKA",
          "name": "阿拉斯加",
          "side": "allies",
          "position": "CC25",
          "heading": 5,
          "speed": 6,
          "asset": "美国-CB-阿拉斯加.png"
        },
        {
          "id": "IBS-U-USN-ERMA-GUAM",
          "name": "关岛",
          "side": "allies",
          "position": "DD25",
          "heading": 5,
          "speed": 6,
          "asset": "美国-CB-关岛.png"
        },
        {
          "id": "IBS-U-USN-ERMA-DES-MOINES",
          "name": "得梅因",
          "side": "allies",
          "position": "V25",
          "heading": 5,
          "speed": 6,
          "asset": "美国-CA-得梅因.png"
        },
        {
          "id": "IBS-U-USN-ERMA-SALEM",
          "name": "塞勒姆",
          "side": "allies",
          "position": "W26",
          "heading": 5,
          "speed": 6,
          "asset": "美国-CA-塞勒姆.png"
        },
        {
          "id": "IBS-U-USN-ERMA-WORCESTER",
          "name": "伍斯特",
          "side": "allies",
          "position": "X26",
          "heading": 5,
          "speed": 6,
          "asset": "美国-CL-伍斯特.png"
        },
        {
          "id": "IBS-U-USN-ERMA-ALLEN-M-SUMNER",
          "name": "艾伦·M·萨姆纳",
          "side": "allies",
          "position": "S26",
          "heading": 5,
          "speed": 6,
          "asset": "美国-DD-艾伦·M·萨姆纳.png"
        },
        {
          "id": "IBS-U-USN-ERMA-INGRAHAM",
          "name": "英格拉罕",
          "side": "allies",
          "position": "T26",
          "heading": 5,
          "speed": 6,
          "asset": "美国-DD-英格拉罕.png"
        },
        {
          "id": "IBS-U-USN-ERMA-COOPER",
          "name": "库珀",
          "side": "allies",
          "position": "U27",
          "heading": 5,
          "speed": 6,
          "asset": "美国-DD-库珀.png"
        }
      ],
      "ai_stats": {
        "games": 10,
        "axis_wins": 3,
        "allies_wins": 0,
        "draws": 7,
        "avg_turns": 12,
        "avg_sunk": {
          "axis": 4.6,
          "allies": 4
        },
        "failures": 0,
        "note": "双 tactical RealisticCommander 自战（balanced 风格，seeds 1..N）；仅供剧本平衡参考，非官方胜率。"
      }
    },
    "IBS-S-FM-01": {
      "id": "IBS-S-FM-01",
      "number": "FM-01",
      "title": "铁底湾的回响·午夜舰队决战（虚构想定）",
      "date": "1944-10-25",
      "status": "playable",
      "source": {
        "document": "user_commissioned_fictional_scenario",
        "status": "design",
        "design_notes": "虚构推演：参考1942-1944所罗门夜战与莱特湾海战编成；编队参考历史雷击编队（挺身攻击队/东京快车/31节伯克/李式战列纵队）。舰船数据全部来自已核验记录（记录手册/舰级卡/二马扩展）。"
      },
      "map_columns": 92,
      "map_rows": 78,
      "printed_columns": 92,
      "printed_rows": 78,
      "turns": 14,
      "visibility": {
        "axis": 18,
        "allies": 22
      },
      "optional_rules": [],
      "available_optional_rules": [
        "hidden_contacts",
        "radar",
        "star_shells",
        "searchlights",
        "malfunction_66",
        "squalls",
        "smoke",
        "silhouettes",
        "hidden_damage",
        "blind_torpedoes"
      ],
      "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 参考历史雷击编队（见各编队注记），仅为真实模式直接开局的默认提案。",
        "engine_default_formations": {
          "axis": [
            {
              "id": "axis-standby-strike",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-HIEI",
                "IBS-U-IJN-KIRISHIMA",
                "IBS-U-IJN-OWARI",
                "IBS-U-IJN-AMAGI",
                "IBS-U-IJN-AKAGI"
              ],
              "note": "挺身夜战战队（阿部弘毅式：高速战巡先行突入）"
            },
            {
              "id": "axis-main-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ERMA-YAMATO",
                "IBS-U-IJN-ERMA-MUSASHI",
                "IBS-U-IJN-ERMA-SHINANO",
                "IBS-U-IJN-NAGATO",
                "IBS-U-IJN-MUTSU"
              ],
              "note": "第一游击部队本队（大和级为中心的战列纵队）"
            },
            {
              "id": "axis-heavy-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ATAGO",
                "IBS-U-IJN-TAKAO",
                "IBS-U-IJN-NACHI",
                "IBS-U-IJN-MYOKO",
                "IBS-U-IJN-HAGURO",
                "IBS-U-IJN-CHOKAI"
              ],
              "note": "重巡战队（直卫警戒列）"
            },
            {
              "id": "axis-light-cruiser-screen",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-AGANO",
                "IBS-U-IJN-JINTSU-I",
                "IBS-U-IJN-SENDAI",
                "IBS-U-IJN-NAGARA"
              ],
              "note": "轻巡警戒队"
            },
            {
              "id": "axis-torpedo-squadron-1",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-ERMA-SHIMAKAZE",
                "IBS-U-IJN-YUKIKAZE",
                "IBS-U-IJN-SHIGURE",
                "IBS-U-IJN-NAGANAMI",
                "IBS-U-IJN-MAKINAMI"
              ],
              "note": "第一雷击队（岛风领雷，东京快车突击队式）"
            },
            {
              "id": "axis-torpedo-squadron-2",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-YUGUMO",
                "IBS-U-IJN-AKIGUMO",
                "IBS-U-IJN-KAZEKUMO",
                "IBS-U-IJN-TAKANAMI",
                "IBS-U-IJN-ASAGUMO"
              ],
              "note": "第二雷击队"
            },
            {
              "id": "axis-old-cruiser-feint",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-FURUTAKA",
                "IBS-U-IJN-KAKO-I",
                "IBS-U-IJN-AOBA",
                "IBS-U-IJN-KINUGASA",
                "IBS-U-IJN-YUBARI",
                "IBS-U-IJN-TENRYU",
                "IBS-U-IJN-TATSUTA"
              ],
              "note": "第三梯队（旧式巡洋舰佯动队）"
            },
            {
              "id": "axis-akizuki-rear",
              "role": "line_ahead",
              "ships": [
                "IBS-U-IJN-AKIZUKI",
                "IBS-U-IJN-TERUZUKI",
                "IBS-U-IJN-NIIZUKI",
                "IBS-U-IJN-WAKATSUKI"
              ],
              "note": "秋月型殿后队（对空警戒/诱饵）"
            }
          ],
          "allies": [
            {
              "id": "allies-fast-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-ERMA-IOWA",
                "IBS-U-USN-ERMA-NEW-JERSEY",
                "IBS-U-USN-ERMA-MISSOURI",
                "IBS-U-USN-ERMA-WISCONSIN",
                "IBS-U-USN-UNNAMED-T01-R03",
                "IBS-U-USN-WASHINGTON",
                "IBS-U-USN-SOUTH-DAKOTA"
              ],
              "note": "TF34 快速战列纵队（李式单纵）"
            },
            {
              "id": "allies-old-battle-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-COLORADO",
                "IBS-U-USN-WEST-VIRGINIA"
              ],
              "note": "旧战列分队（殿后火力线）"
            },
            {
              "id": "allies-big-cruiser-scout",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-UNNAMED-T01-R06",
                "IBS-U-USN-UNNAMED-T01-R07",
                "IBS-U-USN-UNNAMED-T01-R08",
                "IBS-U-USN-ERMA-ALASKA",
                "IBS-U-USN-ERMA-GUAM"
              ],
              "note": "大巡侦察战队（阿拉斯加级+列克星敦级）"
            },
            {
              "id": "allies-heavy-cruiser-north",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-SAN-FRANCISCO",
                "IBS-U-USN-MINNEAPOLIS",
                "IBS-U-USN-NEW-ORLEANS",
                "IBS-U-USN-UNNAMED-T01-R12",
                "IBS-U-USN-UNNAMED-T01-R13",
                "IBS-U-USN-UNNAMED-T01-R20"
              ],
              "note": "北线重巡队"
            },
            {
              "id": "allies-heavy-cruiser-south",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-PENSACOLA",
                "IBS-U-USN-SALT-LAKE-CITY",
                "IBS-U-USN-NORTHAMPTON",
                "IBS-U-USN-VINCENNES",
                "IBS-U-USN-QUINCY",
                "IBS-U-USN-ASTORIA",
                "IBS-U-RAN-CANBERRA",
                "IBS-U-RAN-AUSTRALIA"
              ],
              "note": "南线重巡队（含澳舰，呼应萨沃岛之夜）"
            },
            {
              "id": "allies-light-cruiser-line",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-HELENA",
                "IBS-U-USN-ST-LOUIS",
                "IBS-U-USN-HONOLULU",
                "IBS-U-USN-BOISE",
                "IBS-U-USN-UNNAMED-T01-R23",
                "IBS-U-USN-UNNAMED-T01-R24",
                "IBS-U-USN-UNNAMED-T01-R25",
                "IBS-U-USN-UNNAMED-T01-R26",
                "IBS-U-USN-UNNAMED-T01-R27",
                "IBS-U-USN-UNNAMED-T01-R28",
                "IBS-U-USN-UNNAMED-T01-R29"
              ],
              "note": "轻巡纵列（布鲁克林/克利夫兰/亚特兰大级）"
            },
            {
              "id": "allies-desron-23",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-CF-AUSBURNE",
                "IBS-U-USN-CLAXTON",
                "IBS-U-USN-DYSON",
                "IBS-U-USN-CONVERSE",
                "IBS-U-USN-SPENCE"
              ],
              "note": "第 23 驱逐舰中队（伯克「31 节」五舰单纵）"
            },
            {
              "id": "allies-desron-screen",
              "role": "line_ahead",
              "ships": [
                "IBS-U-USN-NICHOLAS",
                "IBS-U-USN-OBANNON",
                "IBS-U-USN-TAYLOR",
                "IBS-U-USN-LA-VALLETTE",
                "IBS-U-USN-UNNAMED-T01-R51",
                "IBS-U-USN-UNNAMED-T01-R52"
              ],
              "note": "警戒驱逐队（前哨/鱼雷反击）"
            }
          ]
        }
      },
      "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 15,
        "draw_if_margin_below": 15,
        "evaluated_at": "end_of_turn_14"
      },
      "special_rules": [
        {
          "id": "IBS-S-FM-01-R1",
          "text": "本想定为虚构推演（不属于官方想定手册）：1944 年 10 月 25 日夜，联合舰队倾主力突入铁底湾炮击亨德森机场，盟军以全部可用主力舰封锁峡口。"
        },
        {
          "id": "IBS-S-FM-01-R2",
          "text": "双方旗舰：联合舰队大和（第一游击部队本队），盟军衣阿华（TF34 快速战列纵队）。"
        },
        {
          "id": "IBS-S-FM-01-R3",
          "text": "战场为 92×78 大战场海图；能见度日军 18 格、盟军 22 格（盟军雷达优势）。"
        },
        {
          "id": "IBS-S-FM-01-R4",
          "text": "编队提案参考历史雷击编队：日军挺身夜战战队（阿部 弘毅式）、第一/第二雷击队（田中赖三东京快车式）；盟军 TF34 战列纵队（李 式）、第 23 驱逐舰中队（伯克「31 节」单纵）。"
        },
        {
          "id": "IBS-S-FM-01-R5",
          "text": "14 回合结束时统计胜利分：每造成 3 点船体损失计入 1 分；领先 15 分或更多为胜利者，其他结果为平局。"
        }
      ],
      "ships": [
        {
          "id": "IBS-U-IJN-HIEI",
          "name": "比叡",
          "side": "axis",
          "position": "E20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-比叡.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-KIRISHIMA",
          "name": "雾岛",
          "side": "axis",
          "position": "E19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-雾岛.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-OWARI",
          "name": "尾张",
          "side": "axis",
          "position": "E18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BC-尾张.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-AMAGI",
          "name": "天城",
          "side": "axis",
          "position": "E17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BC-天城.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-AKAGI",
          "name": "赤城",
          "side": "axis",
          "position": "E16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BC-赤城.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-ERMA-YAMATO",
          "name": "大和",
          "side": "axis",
          "position": "J20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-大和-二马.png",
          "flagship": true
        },
        {
          "id": "IBS-U-IJN-ERMA-MUSASHI",
          "name": "武藏",
          "side": "axis",
          "position": "J19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-武藏.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-ERMA-SHINANO",
          "name": "信浓",
          "side": "axis",
          "position": "J18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-信浓.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-NAGATO",
          "name": "长门",
          "side": "axis",
          "position": "J17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-长门.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-MUTSU",
          "name": "陆奥",
          "side": "axis",
          "position": "J16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-BB-陆奥.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-ATAGO",
          "name": "爱宕",
          "side": "axis",
          "position": "O20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-爱宕.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-TAKAO",
          "name": "高雄",
          "side": "axis",
          "position": "O19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-高雄.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-NACHI",
          "name": "那智",
          "side": "axis",
          "position": "O18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-那智.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-MYOKO",
          "name": "妙高",
          "side": "axis",
          "position": "O17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-妙高.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-HAGURO",
          "name": "羽黑",
          "side": "axis",
          "position": "O16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-羽黑.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-CHOKAI",
          "name": "鸟海",
          "side": "axis",
          "position": "O15",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-鸟海.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-AGANO",
          "name": "阿贺野",
          "side": "axis",
          "position": "T20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-阿贺野.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-JINTSU-I",
          "name": "神通(I)",
          "side": "axis",
          "position": "T19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-神通1.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-SENDAI",
          "name": "川内",
          "side": "axis",
          "position": "T18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-川内.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-NAGARA",
          "name": "长良",
          "side": "axis",
          "position": "T17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-长良.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-ERMA-SHIMAKAZE",
          "name": "岛风",
          "side": "axis",
          "position": "Y20",
          "heading": 2,
          "speed": 6,
          "asset": "日本-DD-岛风.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-YUKIKAZE",
          "name": "雪风",
          "side": "axis",
          "position": "Y19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-雪风.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-SHIGURE",
          "name": "时雨",
          "side": "axis",
          "position": "Y18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-时雨.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-NAGANAMI",
          "name": "长波",
          "side": "axis",
          "position": "Y17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-长波.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-MAKINAMI",
          "name": "卷波",
          "side": "axis",
          "position": "Y16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-卷波.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-YUGUMO",
          "name": "夕云",
          "side": "axis",
          "position": "DD20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-夕云.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-AKIGUMO",
          "name": "秋云",
          "side": "axis",
          "position": "DD19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-秋云.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-KAZEKUMO",
          "name": "风云",
          "side": "axis",
          "position": "DD18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-风云.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-TAKANAMI",
          "name": "高波",
          "side": "axis",
          "position": "DD17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-高波.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-ASAGUMO",
          "name": "朝云",
          "side": "axis",
          "position": "DD16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-朝云.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-FURUTAKA",
          "name": "古鹰",
          "side": "axis",
          "position": "II20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-古鹰.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-KAKO-I",
          "name": "加古(I)",
          "side": "axis",
          "position": "II19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-加古1.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-AOBA",
          "name": "青叶",
          "side": "axis",
          "position": "II18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-青叶.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-KINUGASA",
          "name": "衣笠",
          "side": "axis",
          "position": "II17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CA-衣笠.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-YUBARI",
          "name": "夕张",
          "side": "axis",
          "position": "II16",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-夕张.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-TENRYU",
          "name": "天龙",
          "side": "axis",
          "position": "II15",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-天龙.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-TATSUTA",
          "name": "龙田",
          "side": "axis",
          "position": "II14",
          "heading": 2,
          "speed": 5,
          "asset": "日本-CL-龙田.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-AKIZUKI",
          "name": "秋月",
          "side": "axis",
          "position": "NN20",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-秋月.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-TERUZUKI",
          "name": "照月",
          "side": "axis",
          "position": "NN19",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-照月.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-NIIZUKI",
          "name": "新月",
          "side": "axis",
          "position": "NN18",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-新月.png",
          "flagship": false
        },
        {
          "id": "IBS-U-IJN-WAKATSUKI",
          "name": "若月",
          "side": "axis",
          "position": "NN17",
          "heading": 2,
          "speed": 5,
          "asset": "日本-DD-若月.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ERMA-IOWA",
          "name": "衣阿华",
          "side": "allies",
          "position": "WW60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-衣阿华.png",
          "flagship": true
        },
        {
          "id": "IBS-U-USN-ERMA-NEW-JERSEY",
          "name": "新泽西",
          "side": "allies",
          "position": "WW61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-新泽西.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ERMA-MISSOURI",
          "name": "密苏里",
          "side": "allies",
          "position": "WW62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-密苏里.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ERMA-WISCONSIN",
          "name": "威斯康星",
          "side": "allies",
          "position": "WW63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-威斯康星.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R03",
          "name": "北卡罗来纳",
          "side": "allies",
          "position": "WW64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-北卡罗来纳.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-WASHINGTON",
          "name": "华盛顿",
          "side": "allies",
          "position": "WW65",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-华盛顿.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-SOUTH-DAKOTA",
          "name": "南达科塔",
          "side": "allies",
          "position": "WW66",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BB-南达科塔.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-COLORADO",
          "name": "科罗拉多",
          "side": "allies",
          "position": "BBB60",
          "heading": 5,
          "speed": 4,
          "asset": "美国-BB-科罗拉多.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-WEST-VIRGINIA",
          "name": "西弗吉尼亚",
          "side": "allies",
          "position": "BBB61",
          "heading": 5,
          "speed": 4,
          "asset": "美国-BB-西弗吉尼亚.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R06",
          "name": "列克星敦",
          "side": "allies",
          "position": "GGG60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BC-列克星敦.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R07",
          "name": "合众国",
          "side": "allies",
          "position": "GGG61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BC-合众国.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R08",
          "name": "宪法",
          "side": "allies",
          "position": "GGG62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-BC-宪法.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ERMA-ALASKA",
          "name": "阿拉斯加",
          "side": "allies",
          "position": "GGG63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CB-阿拉斯加.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ERMA-GUAM",
          "name": "关岛",
          "side": "allies",
          "position": "GGG64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CB-关岛.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-SAN-FRANCISCO",
          "name": "旧金山",
          "side": "allies",
          "position": "LLL60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-旧金山.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-MINNEAPOLIS",
          "name": "明尼阿波利斯",
          "side": "allies",
          "position": "LLL61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-明尼阿波里斯.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-NEW-ORLEANS",
          "name": "新奥尔良",
          "side": "allies",
          "position": "LLL62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-新奥尔良.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R12",
          "name": "芝加哥",
          "side": "allies",
          "position": "LLL63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-芝加哥.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R13",
          "name": "休斯顿",
          "side": "allies",
          "position": "LLL64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-休斯顿.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R20",
          "name": "波特兰",
          "side": "allies",
          "position": "LLL65",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-波特兰.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-PENSACOLA",
          "name": "彭萨科拉",
          "side": "allies",
          "position": "QQQ60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-彭萨科拉.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-SALT-LAKE-CITY",
          "name": "盐湖城",
          "side": "allies",
          "position": "QQQ61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-盐湖城.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-NORTHAMPTON",
          "name": "北安普敦",
          "side": "allies",
          "position": "QQQ62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-北安普敦.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-VINCENNES",
          "name": "文森斯",
          "side": "allies",
          "position": "QQQ63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-文森斯.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-QUINCY",
          "name": "昆西",
          "side": "allies",
          "position": "QQQ64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-昆西.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ASTORIA",
          "name": "阿斯托里亚",
          "side": "allies",
          "position": "QQQ65",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CA-阿斯托里亚.png",
          "flagship": false
        },
        {
          "id": "IBS-U-RAN-CANBERRA",
          "name": "堪培拉",
          "side": "allies",
          "position": "QQQ66",
          "heading": 5,
          "speed": 5,
          "asset": "澳大利亚-CA-堪培拉.png",
          "flagship": false
        },
        {
          "id": "IBS-U-RAN-AUSTRALIA",
          "name": "澳大利亚",
          "side": "allies",
          "position": "QQQ67",
          "heading": 5,
          "speed": 5,
          "asset": "澳大利亚-CA-堪培拉.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-HELENA",
          "name": "海伦娜",
          "side": "allies",
          "position": "VVV60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-海伦娜.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-ST-LOUIS",
          "name": "圣路易斯",
          "side": "allies",
          "position": "VVV61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-圣路易斯.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-HONOLULU",
          "name": "火奴鲁鲁",
          "side": "allies",
          "position": "VVV62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-火奴鲁鲁.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-BOISE",
          "name": "博伊西",
          "side": "allies",
          "position": "VVV63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-博伊西.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R23",
          "name": "亚特兰大",
          "side": "allies",
          "position": "VVV64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-亚特兰大.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R24",
          "name": "朱诺",
          "side": "allies",
          "position": "VVV65",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-朱诺.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R25",
          "name": "圣胡安",
          "side": "allies",
          "position": "VVV66",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-圣胡安.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R26",
          "name": "克利夫兰",
          "side": "allies",
          "position": "VVV67",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-克利夫兰.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R27",
          "name": "哥伦比亚",
          "side": "allies",
          "position": "VVV68",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-哥伦比亚.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R28",
          "name": "蒙彼利埃",
          "side": "allies",
          "position": "VVV69",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-蒙彼利埃.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R29",
          "name": "丹弗",
          "side": "allies",
          "position": "VVV70",
          "heading": 5,
          "speed": 5,
          "asset": "美国-CL-丹佛.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-CF-AUSBURNE",
          "name": "查尔斯·奥斯本",
          "side": "allies",
          "position": "AAAA60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-查尔斯·奥斯本.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-CLAXTON",
          "name": "克拉克斯顿",
          "side": "allies",
          "position": "AAAA61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-克拉克斯顿.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-DYSON",
          "name": "戴森",
          "side": "allies",
          "position": "AAAA62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-戴森.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-CONVERSE",
          "name": "康弗斯",
          "side": "allies",
          "position": "AAAA63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-康弗斯.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-SPENCE",
          "name": "斯彭斯",
          "side": "allies",
          "position": "AAAA64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-斯彭斯.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-NICHOLAS",
          "name": "尼古拉斯",
          "side": "allies",
          "position": "FFFF60",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-尼古拉斯.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-OBANNON",
          "name": "奥班农",
          "side": "allies",
          "position": "FFFF61",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-奥班农.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-TAYLOR",
          "name": "泰勒",
          "side": "allies",
          "position": "FFFF62",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-泰勒.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-LA-VALLETTE",
          "name": "拉瓦利特",
          "side": "allies",
          "position": "FFFF63",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-拉瓦利特.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R51",
          "name": "邓拉普",
          "side": "allies",
          "position": "FFFF64",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-邓拉普.png",
          "flagship": false
        },
        {
          "id": "IBS-U-USN-UNNAMED-T01-R52",
          "name": "格里德利",
          "side": "allies",
          "position": "FFFF65",
          "heading": 5,
          "speed": 5,
          "asset": "美国-DD-格里德利.png",
          "flagship": false
        }
      ]
    }
  }, templates: {
    "dd-german-1940": {
      "type": "DD",
      "hull": 6,
      "speed_track": [6, 6, 6],
      "primary_gf": 2,
      "primary_caliber": 5,
      "torpedoes": 2,
      "torpedo_type": "us-21-mk14-1928",
      "vp": 4
    },
    "dd-british-1940": {
      "type": "DD",
      "hull": 6,
      "speed_track": [6, 6, 6],
      "primary_gf": 3,
      "primary_caliber": 4.7,
      "torpedoes": 2,
      "torpedo_type": "us-21-mk14-1928",
      "vp": 3
    },
    "ca-japanese-1942": {
      "type": "CA",
      "hull": 11,
      "speed_track": [6, 5, 5],
      "primary_gf": 16,
      "primary_caliber": 8,
      "secondary_gf": 2,
      "belt_armor": 3,
      "torpedoes": 2,
      "torpedo_type": "jp-24-type93",
      "vp": 11
    },
    "ca-american-1942": {
      "type": "CA",
      "hull": 11,
      "speed_track": [6, 5, 5],
      "primary_gf": 15,
      "primary_caliber": 8,
      "secondary_gf": 2,
      "belt_armor": 4,
      "torpedoes": 0,
      "vp": 11
    },
    "cl-american-1942": {
      "type": "CL",
      "hull": 10,
      "speed_track": [6, 5, 5],
      "primary_gf": 14,
      "primary_caliber": 6,
      "secondary_gf": 2,
      "belt_armor": 3,
      "torpedoes": 0,
      "vp": 9
    },
    "dd-japanese-1942": {
      "type": "DD",
      "hull": 6,
      "speed_track": [6, 6, 5],
      "primary_gf": 3,
      "primary_caliber": 5,
      "torpedoes": 2,
      "torpedo_type": "jp-24-type93",
      "vp": 4
    },
    "dd-american-1942": {
      "type": "DD",
      "hull": 6,
      "speed_track": [6, 6, 6],
      "primary_gf": 2,
      "primary_caliber": 5,
      "torpedoes": 2,
      "torpedo_type": "us-21-mk15-1942",
      "vp": 2
    },
    "av-japanese-1942": {
      "type": "AV",
      "hull": 8,
      "speed_track": [5, 5, 4],
      "primary_gf": 2,
      "primary_caliber": 5,
      "torpedoes": 0,
      "vp": 6
    }
  }
}
if (typeof module !== "undefined" && module.exports) module.exports = data
