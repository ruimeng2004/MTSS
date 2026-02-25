#!/bin/bash
# 重新评估checkout失败的案例
# 自动生成于: comprehensive_false_negative_fix.py

set -e

MTSS_DIR=/home/base/mengrui/MTSS
OUTPUT_DIR=$MTSS_DIR/evaluation_output

echo '==================================='
echo '重新评估Checkout失败案例'
echo '==================================='
echo

# qwen30b_edit - 81 个bugs
echo 'Processing qwen30b_edit...'

cat > $MTSS_DIR/checkout_failures_qwen30b_edit.txt << 'EOF'
JacksonDatabind_82
JacksonDatabind_83
JacksonDatabind_34
JacksonDatabind_39
JacksonDatabind_29
JacksonDatabind_75
JacksonDatabind_70
JacksonDatabind_17
JacksonDatabind_63
JacksonDatabind_9
JacksonDatabind_74
JacksonDatabind_32
JacksonDatabind_88
JacksonDatabind_45
JacksonDatabind_85
JacksonDatabind_46
JacksonDatabind_62
JacksonDatabind_98
JacksonDatabind_36
JacksonDatabind_61
JacksonDatabind_71
JacksonDatabind_35
JacksonDatabind_77
JacksonDatabind_47
JacksonDatabind_68
JacksonDatabind_41
JacksonDatabind_69
JacksonDatabind_28
JacksonDatabind_3
JacksonDatabind_8
JacksonDatabind_27
JacksonDatabind_25
JacksonDatabind_19
JacksonDatabind_99
JacksonDatabind_112
JacksonDatabind_57
JacksonDatabind_101
JacksonDatabind_12
JacksonDatabind_97
JacksonDatabind_107
JacksonDatabind_31
JacksonDatabind_56
JacksonDatabind_22
JacksonDatabind_58
JacksonDatabind_42
JacksonDatabind_76
JacksonDatabind_2
JacksonDatabind_52
JacksonDatabind_67
JacksonDatabind_64
JacksonDatabind_100
JacksonDatabind_13
JacksonDatabind_16
JacksonDatabind_44
JacksonDatabind_49
JacksonDatabind_93
JacksonDatabind_102
JacksonDatabind_91
JacksonDatabind_24
JacksonDatabind_48
JacksonDatabind_5
JacksonDatabind_80
JacksonDatabind_37
JacksonDatabind_51
JacksonDatabind_6
JacksonDatabind_14
JacksonDatabind_95
JacksonDatabind_1
JacksonDatabind_104
JacksonDatabind_11
JacksonDatabind_33
JacksonDatabind_7
JacksonDatabind_106
JacksonDatabind_81
JacksonDatabind_4
JacksonDatabind_15
JacksonDatabind_90
JacksonDatabind_54
JacksonDatabind_59
JacksonDatabind_108
JacksonDatabind_96
EOF

# 重新评估 qwen30b_edit
python $MTSS_DIR/evaluate.py \
  --input-batch ppl/result/20260106_113852 \
  --output-dir $OUTPUT_DIR/qwen30b_edit_checkout_fixed \
  --bug-list $MTSS_DIR/checkout_failures_qwen30b_edit.txt \
  --num-workers 32 \
  --force-clean

echo '✓ qwen30b_edit 完成'
echo

# qwencoder_edit - 174 个bugs
echo 'Processing qwencoder_edit...'

cat > $MTSS_DIR/checkout_failures_qwencoder_edit.txt << 'EOF'
JacksonDatabind_82
Chart_21
JacksonDatabind_83
JacksonDatabind_34
Math_91
JacksonDatabind_39
Time_26
JacksonDatabind_29
JacksonDatabind_75
JacksonDatabind_70
JacksonDatabind_17
JacksonDatabind_63
Mockito_7
Time_18
Time_5
JacksonDatabind_9
Chart_17
Mockito_11
Mockito_35
JacksonDatabind_74
Time_27
Chart_10
JacksonDatabind_32
JacksonDatabind_88
Time_1
Chart_4
Math_9
Chart_14
Time_16
Time_13
JacksonDatabind_45
Chart_12
JacksonDatabind_85
JacksonCore_22
Math_86
Mockito_16
Chart_15
JacksonDatabind_46
JacksonDatabind_62
Chart_1
JacksonDatabind_98
Math_97
Math_99
JacksonDatabind_36
JacksonDatabind_61
JacksonDatabind_35
JacksonDatabind_71
Chart_16
Mockito_34
JacksonDatabind_77
JacksonCore_21
JacksonDatabind_47
Math_95
JacksonDatabind_68
Chart_19
Chart_11
Math_98
Mockito_22
JacksonDatabind_41
JacksonDatabind_69
Chart_3
JacksonDatabind_28
Math_93
JacksonDatabind_3
JacksonDatabind_8
Chart_9
JacksonDatabind_27
JacksonDatabind_25
JacksonDatabind_19
Chart_26
Time_12
JacksonDatabind_99
JacksonDatabind_112
JacksonDatabind_57
JacksonDatabind_101
Mockito_5
Time_25
JacksonDatabind_12
JacksonDatabind_97
Chart_18
JacksonDatabind_107
JacksonDatabind_31
JacksonDatabind_56
Mockito_24
Mockito_8
JacksonDatabind_22
JacksonDatabind_58
JacksonDatabind_42
JacksonDatabind_76
Mockito_20
Chart_25
JacksonDatabind_2
Math_84
Mockito_37
JacksonDatabind_52
JacksonDatabind_67
JacksonDatabind_64
Mockito_27
Mockito_6
Mockito_30
JacksonDatabind_100
JacksonDatabind_13
Mockito_4
Mockito_29
Time_20
Mockito_12
Chart_5
Time_23
JacksonDatabind_16
JacksonDatabind_44
JacksonDatabind_49
Chart_24
JacksonDatabind_102
JacksonDatabind_93
Mockito_38
Time_24
JacksonDatabind_91
Time_3
Mockito_13
Time_6
Math_87
Math_89
JacksonDatabind_24
Mockito_3
Time_2
Time_7
JacksonDatabind_48
Chart_2
Math_85
Math_92
Time_17
JacksonDatabind_5
Chart_6
JacksonDatabind_80
JacksonDatabind_37
Time_15
JacksonDatabind_51
Mockito_18
Mockito_33
Math_88
Chart_7
Time_22
JacksonDatabind_6
JacksonDatabind_14
Chart_8
JacksonDatabind_95
JacksonDatabind_1
JacksonDatabind_104
JacksonCore_5
JacksonDatabind_11
JacksonDatabind_33
JacksonDatabind_7
JacksonDatabind_106
JacksonDatabind_81
Math_96
Mockito_1
Time_14
JacksonDatabind_4
Math_90
Mockito_21
Time_19
JacksonCore_26
JacksonDatabind_15
Mockito_28
JacksonDatabind_90
JacksonDatabind_54
JacksonDatabind_59
Time_8
Math_94
Time_4
Chart_13
JacksonDatabind_108
JacksonCore_25
JacksonDatabind_96
EOF

# 重新评估 qwencoder_edit
python $MTSS_DIR/evaluate.py \
  --input-batch ppl/result/20260106_113852 \
  --output-dir $OUTPUT_DIR/qwencoder_edit_checkout_fixed \
  --bug-list $MTSS_DIR/checkout_failures_qwencoder_edit.txt \
  --num-workers 32 \
  --force-clean

echo '✓ qwencoder_edit 完成'
echo

echo 'All reevaluations complete!'