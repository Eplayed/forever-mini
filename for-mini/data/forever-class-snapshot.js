/* 自动生成，勿手改：node wow-forever-web/tools/export-mini.js */
module.exports = {
 "classes": [
  {
   "classId": "warrior",
   "nameCn": "战士",
   "iconKey": "class_warrior"
  },
  {
   "classId": "paladin",
   "nameCn": "圣骑士",
   "iconKey": "class_paladin"
  },
  {
   "classId": "hunter",
   "nameCn": "猎人",
   "iconKey": "class_hunter"
  },
  {
   "classId": "rogue",
   "nameCn": "潜行者",
   "iconKey": "class_rogue"
  },
  {
   "classId": "priest",
   "nameCn": "牧师",
   "iconKey": "class_priest"
  },
  {
   "classId": "shaman",
   "nameCn": "萨满祭司",
   "iconKey": "class_shaman"
  },
  {
   "classId": "mage",
   "nameCn": "法师",
   "iconKey": "class_mage"
  },
  {
   "classId": "warlock",
   "nameCn": "术士",
   "iconKey": "class_warlock"
  },
  {
   "classId": "druid",
   "nameCn": "德鲁伊",
   "iconKey": "class_druid"
  }
 ],
 "races": [
  {
   "id": "orc",
   "nameCn": "兽人",
   "faction": "horde",
   "iconKey": "race_orc_male",
   "classes": [
    "hunter",
    "mage",
    "rogue",
    "shaman",
    "warlock",
    "warrior"
   ],
   "traits": [
    {
     "name": "血性狂怒",
     "passive": false,
     "effect": "攻击强度和法术强度提高10%，持续15秒。",
     "iconKey": null
    },
    {
     "name": "粉碎诅咒",
     "passive": false,
     "effect": "免疫诅咒和灾祸效果，并降低受到的魔法伤害，持续8秒。",
     "iconKey": "spell_nature_removecurse"
    },
    {
     "name": "斧类武器专精",
     "passive": true,
     "effect": "斧类使法术和技能的爆击几率提高1%。",
     "iconKey": null
    },
    {
     "name": "坚韧",
     "passive": true,
     "effect": "昏迷持续时间缩短20%。",
     "iconKey": "inv_helmet_23"
    }
   ]
  },
  {
   "id": "undead",
   "nameCn": "亡灵",
   "faction": "horde",
   "iconKey": "race_undead_male",
   "classes": [
    "mage",
    "paladin",
    "priest",
    "rogue",
    "warlock",
    "warrior"
   ],
   "traits": [
    {
     "name": "被遗忘者的意志",
     "passive": false,
     "effect": "移除魅惑、恐惧和催眠效果。",
     "iconKey": "spell_shadow_raisedead"
    },
    {
     "name": "食尸",
     "passive": false,
     "effect": "吞噬尸体，在持续时间内恢复35%的生命值和法力值。",
     "iconKey": "ability_racial_cannibalize"
    },
    {
     "name": "水下呼吸",
     "passive": true,
     "effect": "在水下的呼吸时间延长300%。",
     "iconKey": "spell_shadow_demonbreath"
    },
    {
     "name": "哀伤之触",
     "passive": true,
     "effect": "你的攻击有时会吸取生命值。",
     "iconKey": "spell_shadow_fingerofdeath"
    }
   ]
  },
  {
   "id": "tauren",
   "nameCn": "牛头人",
   "faction": "horde",
   "iconKey": "race_tauren_male",
   "classes": [
    "druid",
    "hunter",
    "shaman",
    "warrior"
   ],
   "traits": [
    {
     "name": "战争践踏",
     "passive": false,
     "effect": "使附近的敌人昏迷，持续2秒。",
     "iconKey": "ability_warstomp"
    },
    {
     "name": "栽培",
     "passive": false,
     "effect": "额外长出无需草药学即可采集的草药。",
     "iconKey": "inv_misc_flower_01"
    },
    {
     "name": "原野疾驰",
     "passive": true,
     "effect": "持续移动时，移动速度会逐渐提高。",
     "iconKey": "achievement_zone_barrens_01"
    },
    {
     "name": "耐久",
     "passive": true,
     "effect": "总生命值提高5%，命中几率提高1%。",
     "iconKey": "spell_nature_unyeildingstamina"
    }
   ]
  },
  {
   "id": "troll",
   "nameCn": "巨魔",
   "faction": "horde",
   "iconKey": "race_troll_male",
   "classes": [
    "hunter",
    "mage",
    "priest",
    "rogue",
    "shaman",
    "warlock",
    "warrior"
   ],
   "traits": [
    {
     "name": "狂暴",
     "passive": false,
     "effect": "施法速度和攻击速度提高10%，持续10秒。",
     "iconKey": "racial_troll_berserk"
    },
    {
     "name": "极速再生",
     "passive": false,
     "effect": "在持续时间内恢复50%的最大生命值。",
     "iconKey": "ability_racial_regeneratin"
    },
    {
     "name": "野兽杀手",
     "passive": true,
     "effect": "对野兽造成的伤害提高5%。",
     "iconKey": "inv_misc_pelt_bear_ruin_02"
    },
    {
     "name": "再生",
     "passive": true,
     "effect": "在战斗中保持10%的生命值恢复。",
     "iconKey": "spell_nature_regenerate"
    }
   ]
  },
  {
   "id": "skyborne-horde",
   "nameCn": "天裔",
   "faction": "horde",
   "iconKey": null,
   "classes": [
    "druid",
    "hunter",
    "rogue",
    "shaman",
    "warrior"
   ],
   "traits": []
  },
  {
   "id": "human",
   "nameCn": "人类",
   "faction": "alliance",
   "iconKey": "race_human_male",
   "classes": [
    "hunter",
    "mage",
    "paladin",
    "priest",
    "rogue",
    "warlock",
    "warrior"
   ],
   "traits": [
    {
     "name": "生存意志",
     "passive": false,
     "effect": "移除昏迷效果。",
     "iconKey": "spell_shadow_charm"
    },
    {
     "name": "感知",
     "passive": false,
     "effect": "侦测潜行的敌人，持续20秒。",
     "iconKey": "spell_nature_sleep"
    },
    {
     "name": "剑类武器专精",
     "passive": true,
     "effect": "剑类使法术和技能的爆击几率提高2%。",
     "iconKey": "ability_meleedamage"
    },
    {
     "name": "人类精魂",
     "passive": true,
     "effect": "精神提高5%。",
     "iconKey": "inv_enchant_shardbrilliantsmall"
    }
   ]
  },
  {
   "id": "dwarf",
   "nameCn": "矮人",
   "faction": "alliance",
   "iconKey": "race_dwarf_male",
   "classes": [
    "hunter",
    "paladin",
    "priest",
    "rogue",
    "shaman",
    "warrior"
   ],
   "traits": [
    {
     "name": "石像形态",
     "passive": false,
     "effect": "免疫流血、中毒和疾病效果，并降低受到的物理伤害，持续8秒。",
     "iconKey": "spell_shadow_unholystrength"
    },
    {
     "name": "寻找财宝",
     "passive": false,
     "effect": "追踪附近的宝箱。",
     "iconKey": "racial_dwarf_findtreasure"
    },
    {
     "name": "锤类武器专精",
     "passive": true,
     "effect": "锤类使法术和技能的爆击几率提高1%。",
     "iconKey": "inv_hammer_05"
    },
    {
     "name": "王牌猎人",
     "passive": true,
     "effect": "对野兽造成的伤害提高5%。",
     "iconKey": "inv_weapon_rifle_05"
    }
   ]
  },
  {
   "id": "night-elf",
   "nameCn": "暗夜精灵",
   "faction": "alliance",
   "iconKey": null,
   "classes": [
    "druid",
    "hunter",
    "priest",
    "rogue",
    "warrior"
   ],
   "traits": [
    {
     "name": "艾露恩之光",
     "passive": false,
     "effect": "爆击几率提高10%，持续15秒。",
     "iconKey": "spell_nature_moonglow"
    },
    {
     "name": "影遁",
     "passive": false,
     "effect": "在静止时获得潜行状态。",
     "iconKey": "ability_ambush"
    },
    {
     "name": "迅捷",
     "passive": true,
     "effect": "躲闪几率提高1%，移动速度提高2%。",
     "iconKey": "ability_racial_shadowmeld"
    },
    {
     "name": "精灵之魂",
     "passive": true,
     "effect": "死亡时的移动速度提高75%。",
     "iconKey": "spell_nature_wispsplode"
    }
   ]
  },
  {
   "id": "gnome",
   "nameCn": "侏儒",
   "faction": "alliance",
   "iconKey": "race_gnome_male",
   "classes": [
    "mage",
    "priest",
    "rogue",
    "warlock",
    "warrior"
   ],
   "traits": [
    {
     "name": "逃命专家",
     "passive": false,
     "effect": "短暂免疫定身和诱捕效果。",
     "iconKey": "ability_rogue_trip"
    },
    {
     "name": "我知道了！",
     "passive": false,
     "effect": "使接下来的3个法术或技能消耗降低，伤害或治疗效果提高10%。",
     "iconKey": "inv_gnometoy"
    },
    {
     "name": "开阔思维",
     "passive": true,
     "effect": "法力值、怒气值或能量值上限提高5%。",
     "iconKey": "inv_enchant_essenceeternallarge"
    },
    {
     "name": "工程学专精",
     "passive": true,
     "effect": "工程学装置更加可靠。",
     "iconKey": "inv_misc_gear_01"
    }
   ]
  },
  {
   "id": "skyborne-alliance",
   "nameCn": "天裔",
   "faction": "alliance",
   "iconKey": null,
   "classes": [
    "druid",
    "hunter",
    "mage",
    "rogue",
    "warrior"
   ],
   "traits": []
  }
 ],
 "counts": {
  "classes": 9,
  "races": 10
 }
};
