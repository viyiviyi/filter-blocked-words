import re
from pathlib import Path
from typing import List

from modules import script_callbacks, scripts, shared
from modules.paths_internal import data_path

DATA_PATH = Path(data_path)


def get_prompts_by_file(path:Path):
    if path.exists():
        with path.open('r') as f:
            list = f.readlines()
            return [item.strip().lower() for item in list if item.strip() ]
    else:
        return []

blocked_prompts_txt_file = str(DATA_PATH.joinpath('blocked_prompts.txt'))
blocked_negative_prompts_txt_file = str(DATA_PATH.joinpath('blocked_negative_prompts.txt'))

blocked_prompts=get_prompts_by_file(Path(blocked_prompts_txt_file))
blocked_negative_prompts=get_prompts_by_file(Path(blocked_negative_prompts_txt_file))

enable_blocked_prompts = True
enable_empty_prompts = True
enable_repetition_prompts = False

def setVal():
    global blocked_prompts_txt_file
    global blocked_negative_prompts_txt_file
    global blocked_prompts
    global blocked_negative_prompts
    global enable_blocked_prompts
    global enable_empty_prompts
    global enable_repetition_prompts
    
    blocked_prompts_txt_file = shared.opts.data.get('blocked_prompts_txt_file',blocked_prompts_txt_file)
    blocked_negative_prompts_txt_file = shared.opts.data.get('blocked_negative_prompts_txt_file',blocked_negative_prompts_txt_file)
    blocked_prompts=get_prompts_by_file(Path(blocked_prompts_txt_file))
    blocked_negative_prompts=get_prompts_by_file(Path(blocked_negative_prompts_txt_file))
    
    enable_blocked_prompts = shared.opts.data.get('enable_blocked_prompts',enable_blocked_prompts)
    enable_empty_prompts = shared.opts.data.get('enable_empty_prompts',enable_empty_prompts)
    enable_repetition_prompts = shared.opts.data.get('enable_repetition_prompts',enable_repetition_prompts)


split_sign = [',','(',')','[',']','{','}',':','>','\n']
lora_pattern = r'^[\s]*<[^<>]+'
left_symbol = ['[','{','(']
right_symbol = [']','}',')']

repetition_prompts = []

# 把字符串处理成tag或符号
def prompts_to_arr(prompts:str):
    ls = []
    is_lora = False
    if prompts:
        word = ''
        for sub in prompts:
            if sub in split_sign:
                if sub == ':' and re.match(lora_pattern, word):
                    is_lora = True
                if not is_lora:
                    ls.append(word)
                    ls.append(sub)
                    word = ''
                elif sub == '>':
                    is_lora = False
                    word+=sub
                    ls.append(word)
                    word = ''
                else:
                    word+=sub
            else:
                word+=sub
        return [item.strip(' ') for item in ls if item.strip(' ')]
    return []

def get_prompt(input:str):
    return input.strip().lower()

def filter_repetition(prompts:List[str],next:str):
    item = get_prompt(next)
    if item not in split_sign and item in repetition_prompts:
        return prompts,None
    repetition_prompts.append(item)
    return prompts,next
    
def filter_empty(prompts:List[str],tag:str):
    if not prompts: return prompts,tag
    last = get_prompt(prompts[-1])
    item = get_prompt(tag)
    if item == ',' and last == ',':
        return prompts,None
    if item == ',' and last in left_symbol:
        return prompts,None
    if item in right_symbol and last == ',':
        prompts = prompts[:-1]
        return filter_empty(prompts,tag)
    if item in right_symbol and last in left_symbol:
        prompts = prompts[:-1]
        return filter_empty(prompts,tag)
    return prompts,tag

def filter_prompts_list(input:List[str],blocked:List[str]):
    out_prompts:List[str] = []
    for item in input:
        item = item + (' ' if item == ',' else '')
        next_item = item
        is_skip = False
        if enable_blocked_prompts and get_prompt(item) in blocked:
            is_skip = True
        if enable_repetition_prompts:
            _out_prompts,_next = filter_repetition(out_prompts,item)
            out_prompts = _out_prompts
            next_item = _next
        if enable_blocked_prompts and next_item and is_skip:
            _out_prompts,_next = filter_empty(out_prompts,item)
            out_prompts = _out_prompts
            next_item = _next
            is_skip = False
        if next_item and enable_empty_prompts:
            _out_prompts,_next = filter_empty(out_prompts,item)
            out_prompts = _out_prompts
            next_item = _next
        if not next_item:
            continue
        out_prompts.append(item)
    prompts = ''.join(out_prompts)
    return prompts

def filter_prompts(prompts:str,blocked:List[str]):
    if not blocked: return prompts
    arr_prompts = prompts_to_arr(prompts)
    return filter_prompts_list(arr_prompts,blocked)

class emptyFilter(scripts.Script):
    def title(self):
        return "过滤屏蔽词"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def process(self, p):
        for i in range(len(p.all_prompts)):
            p.all_prompts[i] = filter_prompts(p.all_prompts[i],blocked_prompts)

        for i in range(len(p.all_negative_prompts)):
            p.all_negative_prompts[i] = filter_prompts(p.all_negative_prompts[i],blocked_negative_prompts)

def on_ui_settings():
    section = ("prompts-filter", "prompts filter")
    
    shared.opts.add_option("enable_blocked_prompts", shared.OptionInfo(enable_blocked_prompts, "启用过滤屏蔽词", section=section))
    shared.opts.add_option("enable_empty_prompts", shared.OptionInfo(enable_empty_prompts, "启用过滤空标签", section=section))
    shared.opts.add_option("enable_repetition_prompts", shared.OptionInfo(enable_empty_prompts, "启用过滤重复标签", section=section))
    
    shared.opts.add_option("blocked_prompts_txt_file", shared.OptionInfo(blocked_prompts_txt_file, "屏蔽词文件路径", section=section))
    shared.opts.add_option("blocked_negative_prompts_txt_file", shared.OptionInfo(blocked_negative_prompts_txt_file, "反向tag的屏蔽词文件路径", section=section))
    

    shared.opts.onchange('enable_blocked_prompts', setVal)
    shared.opts.onchange('enable_empty_prompts', setVal)
    shared.opts.onchange('enable_repetition_prompts', setVal)
    
    shared.opts.onchange('blocked_prompts_txt_file', setVal)
    shared.opts.onchange('blocked_negative_prompts_txt_file', setVal)

script_callbacks.on_ui_settings(on_ui_settings)