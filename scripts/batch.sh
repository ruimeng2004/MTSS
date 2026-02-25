# //////////////////////////////////////////////////////////////////////////////////#
# NOTE:                                                                             #
# 1. The following setting is for remote model (GPT-4)                              #
#    If you want to use local model (Mixtral), you should:                          #
#    change `--remote_model $remote_model` argument to `--local_model $local_model`,#
#    add `--model_dir $cp_path`,                                                    #
#    delete `--api_key $api_key`,                                                   #
#    change `--chat_mode remote` argument to `--chat_mode local`.                   #
# 2. When conducting experiments on Defects4J,                                      #
#    you can add `--early_stop True` argument to save token consumption.            #
# //////////////////////////////////////////////////////////////////////////////////#

YAML_FILE="config.yaml"

# YAML Parsing
api_key=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['api_key'])")
cp_path=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['cp_path'])")
remote_model=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['remote_model'])")
local_model=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['local_model'])")
max_try=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['max_try'])")
temperature=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['temperature'])")
remote_proxy=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['remote_proxy'])")
local_proxy=$(python3 -c "import yaml; print(yaml.safe_load(open('$YAML_FILE'))['model_config']['local_proxy'])")

### MAIN EXPERIMENT ###

# GPT-4-based D4C on Defects4J
python -m generator.defects4j --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature --chat_mode remote --remote_proxy $remote_proxy
# Mixtral-based D4C on Defects4J
python -m generator.defects4j --cp_path $cp_path --local_model $local_model --max_try $max_try --temperature $temperature --chat_mode local --local_proxy $local_proxy
# GPT-4-based D4C on DebugBench
python -m generator.debugbench --mode agent --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy

### INSIGHT VALIDATION ###

# python -m generator.debugbench --mode agent --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode hybrid --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode reverse --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode located --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy

### ABLATION STUDY ###

# python -m generator.defects4j --ablation comment --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.defects4j --ablation example --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.defects4j --ablation message --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.defects4j --mode pure --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode agent --ablation comment --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode agent --ablation example  --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode agent --ablation message --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
# python -m generator.debugbench --mode pure --api_key $api_key --remote_model $remote_model --max_try $max_try --temperature $temperature  --chat_mode remote --remote_proxy $remote_proxy
