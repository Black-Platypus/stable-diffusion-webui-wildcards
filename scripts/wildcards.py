import os
import random
import sys
import re

from modules import scripts, script_callbacks, shared

warned_about_files = {}
repo_dir = scripts.basedir()
commentString_default = "#"
emptyRex = re.compile(r"^\s*$", re.MULTILINE)

class WildcardsScript(scripts.Script):
    def __init__(self):
        self.commentString = commentString_default

    def title(self):
        return "Simple wildcards"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def replace_wildcard(self, text, gen):
        if " " in text or len(text) == 0:
            return text

        wildcards_dir = shared.cmd_opts.wildcards_dir or os.path.join(repo_dir, "wildcards")

        replacement_file = os.path.join(wildcards_dir, f"{text}.txt")
        if os.path.exists(replacement_file):
            with open(replacement_file, encoding="utf8") as f:
                # print(f"replacing __{text}__")
                replacerText = f.read()
                # print(commentRex, replacerText)
                if(self.commentString and self.commentString != ""):
                    replacerText = re.sub(self.commentRex, "", replacerText)
                lines = replacerText.splitlines()
                # print(lines)
                lines = list(filter(lambda a: not re.match(emptyRex, a), lines))
                # print(lines)
                if(len(lines)<=0):
                    return text
                choice = gen.choice(lines)
                # print(f"replacing __{text}__ with '{choice}'")
                return choice
        else:
            if replacement_file not in warned_about_files:
                print(f"File {replacement_file} not found for the __{text}__ wildcard.", file=sys.stderr)
                warned_about_files[replacement_file] = 1

        return text

    def replace_prompts(self, prompts, seeds):
        res = []
        if hasattr(shared.opts, "wildcards_comment_char"):
            self.commentString = re.escape(shared.opts.wildcards_comment_char)
            self.commentRex = re.compile(f"\\s*{self.commentString}.+$", re.MULTILINE)

        for i, text in enumerate(prompts):
            gen = random.Random()
            gen.seed(seeds[0 if shared.opts.wildcards_same_seed else i])
            rex = re.compile(r'\b__([^\s\r\n]+?)__\b')
            last_index = 0
            m = rex.finditer(text)
            ret = ""
            for match in m:
                # print(match, match.span(0)[0], match.span(0)[1], match[1])
                if(last_index<match.span(0)[0]):
                    ret += text[last_index:match.span(0)[0]]
                # ret += f"(replace {match[1]})"
                ret += self.replace_wildcard(match[1], gen)
                last_index = match.span(0)[1]
            if(last_index<len(text)):
                ret += text[last_index:]
            res.append(ret)
            # res.append("".join(self.replace_wildcard(chunk, gen) for chunk in text.split("__")))

        return res

    def apply_wildcards(self, p, attr, infotext_suffix, infotext_compare=None):
        if all_original_prompts := getattr(p, attr, None):
            setattr(p, attr, self.replace_prompts(all_original_prompts, p.all_seeds))
            if (shared.opts.wildcards_write_infotext and all_original_prompts[0] != getattr(p, attr)[0] and
                    (not infotext_compare or p.extra_generation_params.get(f"Wildcard {infotext_compare}", None) != all_original_prompts[0])):
                p.extra_generation_params[f"Wildcard {infotext_suffix}"] = all_original_prompts[0]

    def process(self, p, *args):
        for attr, infotext_suffix, infotext_compare in [
            ('all_prompts', 'prompt', None), ('all_negative_prompts', 'negative prompt', None),
            ('all_hr_prompts', 'hr prompt', 'prompt'), ('all_hr_negative_prompts', 'hr negative prompt', 'negative prompt'),
        ]:
            self.apply_wildcards(p, attr, infotext_suffix, infotext_compare)


def on_ui_settings():
    shared.opts.add_option("wildcards_same_seed", shared.OptionInfo(False, "Use same seed for all images", section=("wildcards", "Wildcards")))
    shared.opts.add_option("wildcards_write_infotext", shared.OptionInfo(True, "Write original prompt to infotext", section=("wildcards", "Wildcards")).info("the original prompt before __wildcards__ are applied"))
    shared.opts.add_option("wildcards_comment_char", shared.OptionInfo(commentString_default, "Char/string to begin a comment", section=("wildcards", "Wildcards")).info("Contents after this will be ignored until the end of the line in replacement files"))


script_callbacks.on_ui_settings(on_ui_settings)