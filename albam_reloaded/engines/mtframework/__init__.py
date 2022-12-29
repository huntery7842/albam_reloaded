from enum import Enum

from .structs.arc import Arc
from .structs.mod_156 import Mod156
from .structs.tex import Tex112


__all__ = (
    "Arc",
    "Mod156",
    "Tex112",
    "FILE_ID_TO_EXTENSION",
    "EXTENSION_TO_FILE_ID",
)


CORRUPTED_ARCS = {
    "uOmf303.arc",
    "s101.arc",  # Not an arc
    "uOmf303.arc" "uOmS103ScrAdj.arc",
    "uOm001f.arc",  # Contains only one model that has one vertex
    "uOmS109_Truck_Rail.arc",  # Same, one model one vertex
}

# Probably due to bad indices, needs investigation
KNOWN_ARC_BLENDER_CRASH = {
    "ev612_00.arc",
    "ev204_00.arc",
    "ev606_00.arc",
    "ev613_00.arc",
    "ev614_00.arc",
    "ev615_00.arc",
    "ev616_00.arc",
    "ev617_00.arc",
    "ev618_00.arc",
    "uOm09882.arc",
    "s109.arc",
    "s119.arc",
    "s300.arc",
    "s301.arc",
    "s303.arc",
    "s304.arc",
    "s305.arc",
    "s310.arc",
    "s311.arc",
    "s312.arc",
    "s315.arc",
    "s403.arc",
    "s404.arc",
    "s600.arc",
    "s702.arc",
    "s706.arc",
}


class Mod156BoneAnimationMapping(Enum):
    """
    Mod156.bones_animation_mapping is an array of 256 bytes. Each index
    correspond to a certain predefined bone type, and it's used to be able to
    transfer animations between models.
    """

    ROOT = 0
    LOWER_SPINE = 1
    UPPER_SPINE = 2
    NECK = 3
    HEAD = 4
    RIGHT_SHOULDER = 5
    RIGHT_UPPER_ARM = 6
    RIGHT_ARM = 7
    RIGHT_WRIST = 8
    RIGHT_HAND = 9
    LEFT_SHOULDER = 10
    LEFT_UPPER_ARM = 11
    LEFT_ARM = 12
    LEFT_WRIST = 13
    LEFT_HAND = 14
    HIPS = 15
    RIGHT_UPPER_LEG = 16
    RIGHT_LEG = 17
    RIGHT_FOOT = 18
    RIGHT_TOE = 19
    LEFT_UPPER_LEG = 20
    LEFT_LEG = 21
    LEFT_FOOT = 22
    LEFT_TOE = 23
    RIGHT_UPPER_THUMB = 24
    RIGHT_MIDDLE_THUMB = 25
    RIGHT_LOWER_THUMB = 26
    RIGHT_UPPER_INDEX_FINGER = 27
    RIGHT_MIDDLE_INDEX_FINGER = 28
    RIGHT_LOWER_INDEX_FINGER = 29
    RIGHT_UPPER_MIDDLE_FINGER = 30
    RIGHT_MIDDLE_MIDDLE_FINGER = 31
    RIGHT_LOWER_MIDDLE_FINGER = 32
    RIGHT_PALM = 33
    RIGHT_UPPER_RING_FINGER = 34
    RIGHT_MIDDLE_RING_FINGER = 35
    RIGHT_LOWER_RING_FINGER = 36
    RIGHT_UPPER_PINKY_FINGER = 37
    RIGHT_MIDDLE_PINKY_FINGER = 38
    RIGHT_LOWER_PINKY_FINGER = 39
    LEFT_UPPER_THUMB = 40
    LEFT_MIDDLE_THUMB = 41
    LEFT_LOWER_THUMB = 42
    LEFT_UPPER_INDEX_FINGER = 43
    LEFT_MIDDLE_INDEX_FINGER = 44
    LEFT_LOWER_INDEX_FINGER = 45
    LEFT_UPPER_MIDDLE_FINGER = 46
    LEFT_MIDDLE_MIDDLE_FINGER = 47
    LEFT_LOWER_MIDDLE_FINGER = 48
    LEFT_PALM = 49
    LEFT_UPPER_RING_FINGER = 50
    LEFT_MIDDLE_RING_FINGER = 51
    LEFT_LOWER_RING_FINGER = 52
    LEFT_UPPER_PINKY_FINGER = 53
    LEFT_MIDDLE_PINKY_FINGER = 54
    LEFT_LOWER_PINKY_FINGER = 55
    RIGHT_EYE = 56
    LEFT_EYE = 57
    RIGHT_EYELID = 58
    LEFT_EYELID = 59
    JAW = 60
    UNK_61 = 61
    RIGHT_SHOULDER_DEFORM = 62
    RIGHT_ELBOW_DEFORM = 63
    LEFT_SHOULDER_DEFORM = 64
    LEFT_ELBOW_DEFORM = 65
    RIGHT_BUTT_CHEEK = 66
    LEFT_BUTT_CHEEK = 67
    RIGHT_KNEE = 68
    LEFT_KNEE = 69
    RIGHT_UPPER_ARM_DEFORM_1 = 70
    RIGHT_UPPER_ARM_DEFORM_2 = 71
    RIGHT_UPPER_ARM_DEFORM_3 = 72
    RIGHT_UPPER_ARM_DEFORM_4 = 73
    RIGHT_ARM_DEFORM_1 = 74
    RIGHT_ARM_DEFORM_2 = 75
    LEFT_UPPER_ARM_DEFORM_1 = 76
    LEFT_UPPER_ARM_DEFORM_2 = 77
    LEFT_UPPER_ARM_DEFORM_3 = 78
    LEFT_UPPER_ARM_DEFORM_4 = 79
    LEFT_ARM_DEFORM_1 = 80
    LEFT_ARM_DEFORM_2 = 81
    UNK_82 = 82
    UNK_83 = 83
    UNK_84 = 84
    UNK_85 = 85
    UNK_86 = 86
    UNK_87 = 87
    UNK_88 = 88
    UNK_89 = 89
    UNK_90 = 90
    UNK_91 = 91
    UNK_92 = 92
    UNK_93 = 93
    UNK_94 = 94
    UNK_95 = 95
    UNK_96 = 96
    UNK_97 = 97
    UNK_98 = 98
    UNK_99 = 99
    RIGHT_THUMB = 100
    LEFT_THUMB = 101
    RIGHT_BACKPACK_STRIP = 102
    LEFT_BACKPACK_STRIP = 103
    UNK_104 = 104
    UNK_105 = 105
    UNK_106 = 106
    UNK_107 = 107
    BACK_ACCESORIES_PARENT = 108
    BACK_ACCESORIES = 109
    RIGHT_BACK_ACCESORY_1_PARENT = 110
    RIGHT_BACK_ACCESORY_1 = 111
    RIGHT_BACK_ACCESORY_2_PARENT = 112
    RIGHT_BACK_ACCESORY_2 = 113
    BACK_LEFT_KNIFE_PARENT = 114
    BACK_LEFT_KNIFE = 115
    RIGHT_BACKPACK_STRIP_BACK_1_PARENT = 116
    RIGHT_BACKPACK_STRIP_BACK_1 = 117
    HAIR_FOREHEAD_LEFT_PARENT = 118
    HAIR_FOREHEAD_LEFT = 119
    HAIR_FOREHAD_RIGHT_PARENT = 120
    HAIR_FOREHAD_RIGHT = 121
    HAIR_NAPE_PARENT = 122
    HAIR_NAPE = 123
    HAIR_BACK_PARENT = 124
    HAIR_BACK = 125
    HAIR_UP_1_PARENT = 126
    HAIR_UP_1 = 127
    HAIR_UP_2_PARENT = 128
    HAIR_UP_2 = 129
    HAIR_FOREHEAD = 130
    UNK_131 = 131
    UNK_132 = 132
    UNK_133 = 133
    UNK_134 = 134
    UNK_135 = 135
    UNK_136 = 136
    UNK_137 = 137
    UNK_138 = 138
    UNK_139 = 139
    UNK_140 = 140
    UNK_141 = 141
    UNK_142 = 142
    UNK_143 = 143
    UNK_144 = 144
    UNK_145 = 145
    UNK_146 = 146
    UNK_147 = 147
    UNK_148 = 148
    UNK_149 = 149
    UNK_150 = 150
    UNK_151 = 151
    UNK_152 = 152
    UNK_153 = 153
    UNK_154 = 154
    UNK_155 = 155
    UNK_156 = 156
    UNK_157 = 157
    UNK_158 = 158
    UNK_159 = 159
    UNK_160 = 160
    UNK_161 = 161
    UNK_162 = 162
    UNK_163 = 163
    UNK_164 = 164
    UNK_165 = 165
    UNK_166 = 166
    UNK_167 = 167
    UNK_168 = 168
    UNK_169 = 169
    UNK_170 = 170
    UNK_171 = 171
    UNK_172 = 172
    UNK_173 = 173
    UNK_174 = 174
    UNK_175 = 175
    UNK_176 = 176
    UNK_177 = 177
    UNK_178 = 178
    UNK_179 = 179
    RIGHT_INNER_EYEBROW = 180
    RIGHT_OUTER_EYEBROW = 181
    LEFT_INNER_EYEBROW = 182
    LEFT_OUTER_EYEBROW = 183
    RIGHT_LOWER_EYELID = 184
    LEFT_LOWER_EYELID = 185
    RIGHT_UPPER_CHEEK = 186
    LEFT_UPPER_CHEEK = 187
    RIGHT_UPPER_OUTER_CHEEK = 188
    LEFT_UPPER_OUTER_CHEEK = 189
    RIGHT_NOSE = 190
    LEFT_NOSE = 191
    RIGHT_OUTER_LIP = 192
    RIGHT_UPPER_LIP = 193
    UPPER_LIP = 194
    LEFT_UPPER_LIP = 195
    LEFT_OUTER_LIP = 196
    LEFT_OUTER_LOWER_LIP = 197
    LOWER_LIP = 198
    LEFT_LOWER_LIP = 199
    RIGHT_LOWER_CHEEK = 200
    LEFT_LOWER_CHEEK = 201
    UNK_202 = 202
    UNK_203 = 203
    UNK_204 = 204
    UNK_205 = 205
    UNK_206 = 206
    UNK_207 = 207
    UNK_208 = 208
    UNK_209 = 209
    UNK_210 = 210
    UNK_211 = 211
    UNK_212 = 212
    UNK_213 = 213
    UNK_214 = 214
    UNK_215 = 215
    UNK_216 = 216
    UNK_217 = 217
    UNK_218 = 218
    UNK_219 = 219
    UNK_220 = 220
    UNK_221 = 221
    UNK_222 = 222
    UNK_223 = 223
    UNK_224 = 224
    UNK_225 = 225
    UNK_226 = 226
    UNK_227 = 227
    UNK_228 = 228
    UNK_229 = 229
    UNK_230 = 230
    UNK_231 = 231
    UNK_232 = 232
    UNK_233 = 233
    UNK_234 = 234
    UNK_235 = 235
    UNK_236 = 236
    UNK_237 = 237
    UNK_238 = 238
    UNK_239 = 239
    UNK_240 = 240
    UNK_241 = 241
    UNK_242 = 242
    UNK_243 = 243
    UNK_244 = 244
    UNK_245 = 245
    UNK_246 = 246
    UNK_247 = 247
    UNK_248 = 248
    UNK_249 = 249
    UNK_250 = 250
    UNK_251 = 251
    UNK_252 = 252
    UNK_253 = 253
    UNK_254 = 254
    UNK_255 = 255


BONE_GROUP_MAIN = {
    "ROOT",
    "LOWER_SPINE",
    "UPPER_SPINE",
    "NECK",
    "HEAD",
    "RIGHT_SHOULDER",
    "RIGHT_UPPER_ARM",
    "RIGHT_ARM",
    "RIGHT_WRIST",
    "RIGHT_HAND",
    "LEFT_SHOULDER",
    "LEFT_UPPER_ARM",
    "LEFT_ARM",
    "LEFT_WRIST",
    "LEFT_HAND",
    "HIPS",
    "RIGHT_UPPER_LEG",
    "RIGHT_LEG",
    "RIGHT_FOOT",
    "RIGHT_TOE",
    "LEFT_UPPER_LEG",
    "LEFT_LEG",
    "LEFT_FOOT",
    "LEFT_TOE",
}

BONE_GROUP_ARMS = {
    "RIGHT_SHOULDER_DEFORM",
    "RIGHT_ELBOW_DEFORM",
    "LEFT_SHOULDER_DEFORM",
    "LEFT_ELBOW_DEFORM",
    "RIGHT_UPPER_ARM_DEFORM_1",
    "RIGHT_UPPER_ARM_DEFORM_2",
    "RIGHT_UPPER_ARM_DEFORM_3",
    "RIGHT_UPPER_ARM_DEFORM_4",
    "RIGHT_ARM_DEFORM_1",
    "RIGHT_ARM_DEFORM_2",
    "LEFT_UPPER_ARM_DEFORM_1",
    "LEFT_UPPER_ARM_DEFORM_2",
    "LEFT_UPPER_ARM_DEFORM_3",
    "LEFT_UPPER_ARM_DEFORM_4",
    "LEFT_ARM_DEFORM_1",
    "LEFT_ARM_DEFORM_2",
}

BONE_GROUP_LEGS = {
    "RIGHT_BUTT_CHEEK",
    "LEFT_BUTT_CHEEK",
    "RIGHT_KNEE",
    "LEFT_KNEE",
}


BONE_GROUP_HANDS = {
    "RIGHT_THUMB",
    "LEFT_THUMB",
    "RIGHT_UPPER_THUMB",
    "RIGHT_MIDDLE_THUMB",
    "RIGHT_LOWER_THUMB",
    "RIGHT_UPPER_INDEX_FINGER",
    "RIGHT_MIDDLE_INDEX_FINGER",
    "RIGHT_LOWER_INDEX_FINGER",
    "RIGHT_UPPER_MIDDLE_FINGER",
    "RIGHT_MIDDLE_MIDDLE_FINGER",
    "RIGHT_LOWER_MIDDLE_FINGER",
    "RIGHT_PALM",
    "RIGHT_UPPER_RING_FINGER",
    "RIGHT_MIDDLE_RING_FINGER",
    "RIGHT_LOWER_RING_FINGER",
    "RIGHT_UPPER_PINKY_FINGER",
    "RIGHT_MIDDLE_PINKY_FINGER",
    "RIGHT_LOWER_PINKY_FINGER",
    "LEFT_UPPER_THUMB",
    "LEFT_MIDDLE_THUMB",
    "LEFT_LOWER_THUMB",
    "LEFT_UPPER_INDEX_FINGER",
    "LEFT_MIDDLE_INDEX_FINGER",
    "LEFT_LOWER_INDEX_FINGER",
    "LEFT_UPPER_MIDDLE_FINGER",
    "LEFT_MIDDLE_MIDDLE_FINGER",
    "LEFT_LOWER_MIDDLE_FINGER",
    "LEFT_PALM",
    "LEFT_UPPER_RING_FINGER",
    "LEFT_MIDDLE_RING_FINGER",
    "LEFT_LOWER_RING_FINGER",
    "LEFT_UPPER_PINKY_FINGER",
    "LEFT_MIDDLE_PINKY_FINGER",
    "LEFT_LOWER_PINKY_FINGER",
}

BONE_GROUP_FACIAL_BASIC = {
    "RIGHT_EYE",
    "LEFT_EYE",
    "RIGHT_EYELID",
    "LEFT_EYELID",
    "JAW",
}

BONE_GROUP_HAIR = {
    "HAIR_FOREHEAD_LEFT_PARENT",
    "HAIR_FOREHEAD_LEFT",
    "HAIR_FOREHAD_RIGHT_PARENT",
    "HAIR_FOREHAD_RIGHT",
    "HAIR_NAPE_PARENT",
    "HAIR_NAPE",
    "HAIR_BACK_PARENT",
    "HAIR_BACK",
    "HAIR_UP_1_PARENT",
    "HAIR_UP_1",
    "HAIR_UP_2_PARENT",
    "HAIR_UP_2",
    "HAIR_FOREHEAD",
}

BONE_GROUP_FACIAL = {
    "RIGHT_INNER_EYEBROW",
    "RIGHT_OUTER_EYEBROW",
    "LEFT_INNER_EYEBROW",
    "LEFT_OUTER_EYEBROW",
    "RIGHT_LOWER_EYELID",
    "LEFT_LOWER_EYELID",
    "RIGHT_UPPER_CHEEK",
    "LEFT_UPPER_CHEEK",
    "RIGHT_UPPER_OUTER_CHEEK",
    "LEFT_UPPER_OUTER_CHEEK",
    "RIGHT_NOSE",
    "LEFT_NOSE",
    "RIGHT_OUTER_LIP",
    "RIGHT_UPPER_LIP",
    "UPPER_LIP",
    "LEFT_UPPER_LIP",
    "LEFT_OUTER_LIP",
    "LEFT_OUTER_LOWER_LIP",
    "LOWER_LIP",
    "LEFT_LOWER_LIP",
    "RIGHT_LOWER_CHEEK",
    "LEFT_LOWER_CHEEK",
}

BONE_GROUP_ACCESORIES = {
    "RIGHT_BACKPACK_STRIP",
    "LEFT_BACKPACK_STRIP",
    "BACK_ACCESORIES_PARENT",
    "BACK_ACCESORIES",
    "RIGHT_BACK_ACCESORY_1_PARENT",
    "RIGHT_BACK_ACCESORY_1",
    "RIGHT_BACK_ACCESORY_2_PARENT",
    "RIGHT_BACK_ACCESORY_2",
    "BACK_LEFT_KNIFE_PARENT",
    "BACK_LEFT_KNIFE",
    "RIGHT_BACKPACK_STRIP_BACK_1_PARENT",
    "RIGHT_BACKPACK_STRIP_BACK_1",
}

# Iterate over all BONE_GROUP_* sets and create a dict
# with bone_indices as keys and group_name as value
BONE_INDEX_TO_GROUP = {}
for group_name, set_of_strings in dict(vars()).items():
    if not group_name.startswith("BONE_GROUP_"):
        continue
    # verify that groups use a correct enum
    bone_enums = {getattr(Mod156BoneAnimationMapping, field_name) for field_name in set_of_strings}
    # check if more than one group share a bone index
    assert all(bone_enum.value not in BONE_INDEX_TO_GROUP for bone_enum in bone_enums)
    for bone_enum in bone_enums:
        BONE_INDEX_TO_GROUP[bone_enum.value] = group_name
