"""Small deterministic shell utilities.

Every command here only prints (or signals through its exit status); none writes files, so each oracle
returns the expected stdout and leaves ctx.state untouched. Oracles compute their result in Python and
never run or parse the shell command.
"""

from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal
import re

from .base import Spec, abspath, quote


def no_fixture(intent, seed, api):
    """Commands that need no files."""


def exactly_one(intent, *names):
    if sum(name in intent for name in names) != 1:
        raise ValueError(f"Give exactly one of {', '.join(names)}")


def only(intent, allowed):
    extra = set(intent) - {"op"} - set(allowed)
    if extra:
        raise ValueError(f"Fields not valid for this form: {sorted(extra)}")


def silent_check(intent, ctx):
    """No output; the observable result is the exit status, which check_intent compares with Spec.returncode."""
    return "", "exact"


VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
RESERVED_VARIABLES = ("PATH", "HOME", "LD_PRELOAD", "LD_LIBRARY_PATH")
# A fractional number of seconds in one canonical spelling (0.5, 1.25; not .5, 0.50, 1.0 or a unit suffix).
FRACTION = re.compile(r"(?:0|[1-9]\d*)\.\d*[1-9]")

# Constants of the evaluation container, probed from the image and hardcoded in the oracles below.
# Accounts (`whoami`, `id`, `groups`, `id root`, `groups root`): the commands run as shellm (uid/gid 1000) with
# no supplementary groups; root is the only other account worth asking about.
USERS = {
    "shellm": {"uid": 1000, "gid": 1000, "groups": [(1000, "shellm")]},
    "root": {"uid": 0, "gid": 0, "groups": [(0, "root")]},
}
CONTAINER_USER = "shellm"
# Environment (`env`): shellbench/worker.py passes exactly these variables, and bash adds PWD, SHLVL and `_` to
# the environment of every program it starts.
CONTAINER_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/home/shellm", "LC_ALL": "C", "LANG": "C",
                 "TZ": "UTC", "TERM": "dumb"}
SHELL_ENV = {"PWD": "/workspace"}
# bash bookkeeping whose value depends on how the listing program was started: `_` is the path of the program
# (env or printenv), and SHLVL drops to 0 when a subshell execs its last command, e.g. `(unset HOME; printenv)`.
# The first choice is what the canonical command produces.
BOOKKEEPING = {"_": ("/usr/bin/env", "/usr/bin/printenv"), "SHLVL": ("1", "0")}


def env_lines(variables):
    return "".join(f"{name}={value}\n" for name, value in variables.items())


# --- echo -------------------------------------------------------------------------------------------

def echo_render(intent):
    return "echo" + (" -n" if intent.get("no_newline") else "") + " " + quote(intent["text"])


def echo_validation(intent):
    if intent["text"].startswith("-") or "\\" in intent["text"]:
        raise ValueError("echo text must not start with a dash or contain backslashes")


def echo_check(intent, ctx):
    return intent["text"] + ("" if intent.get("no_newline") else "\n"), "exact"


# --- printf -----------------------------------------------------------------------------------------

PRINTF_TOKEN = re.compile(r"%%|%[-0]?\d*(?:\.\d+)?[sdf]|\\[nt\\]|[^%\\]")
CONVERSION = re.compile(r"%([-0]?)(\d*)(?:\.(\d+))?([sdf])")
ESCAPES = {"\\n": "\n", "\\t": "\t", "\\\\": "\\", "%%": "%"}


def printf_tokens(fmt):
    """Split a restricted printf format: %s/%d/%f with an optional - or 0 flag, width and (for %f) precision,
    %%, the escapes \\n, \\t, \\\\, and ordinary characters."""
    tokens = PRINTF_TOKEN.findall(fmt)
    if "".join(tokens) != fmt:
        raise ValueError(f"Unsupported printf format: {fmt!r}")
    return tokens


def is_rounding_tie(value, precision):
    scaled = Decimal(value).scaleb(precision)
    return scaled - scaled.to_integral_value(rounding=ROUND_FLOOR) == Decimal("0.5")


def fixed_point(value, precision):
    """%.Nf of a decimal string. Ties are rejected by validation, so the binary rounding of printf cannot differ."""
    return str(Decimal(value).quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_EVEN))


def printf_render(intent):
    fmt = intent["format"]
    return "printf " + ("-- " if fmt.startswith("-") else "") + " ".join(quote(v) for v in [fmt] + intent.get("arguments", []))


def printf_validation(intent):
    specs = [CONVERSION.fullmatch(t) for t in printf_tokens(intent["format"]) if CONVERSION.fullmatch(t)]
    arguments = intent.get("arguments", [])
    if not specs and arguments:
        raise ValueError("printf arguments need a conversion in the format")
    if specs and (not arguments or len(arguments) % len(specs)):
        raise ValueError("printf needs a whole number of argument groups for the format")
    for spec in specs:
        flags, width, precision, kind = spec.groups()
        if (flags == "0" and kind == "s") or (precision and kind != "f") or int(width or 0) > 40:
            raise ValueError(f"Unsupported conversion {spec.group(0)}")
    for index, value in enumerate(arguments):
        flags, width, precision, kind = specs[index % len(specs)].groups()
        if kind == "d" and not re.fullmatch(r"-?\d{1,15}", value):
            raise ValueError(f"%d needs a decimal integer argument, got {value!r}")
        if kind == "f":
            if not re.fullmatch(r"\d{1,6}(?:\.\d{1,6})?", value):
                raise ValueError(f"%f needs a short nonnegative decimal argument, got {value!r}")
            if is_rounding_tie(value, int(precision) if precision else 6):
                raise ValueError(f"{value} is a rounding tie at this precision; printf's binary rounding is not portable")


def printf_convert(spec, value):
    flags, width, precision, kind = spec.groups()
    if kind == "s":
        text = value
    elif kind == "d":
        text = str(int(value))
    else:
        text = fixed_point(value, int(precision) if precision else 6)
    width = int(width or 0)
    if len(text) >= width:
        return text
    if flags == "-":
        return text.ljust(width)
    if flags == "0":
        sign = "-" if text.startswith("-") else ""
        return sign + text[len(sign):].rjust(width - len(sign), "0")
    return text.rjust(width)


def printf_check(intent, ctx):
    tokens = printf_tokens(intent["format"])
    arguments = list(intent.get("arguments", []))
    out = []
    # printf reuses the format until every argument is consumed (once if there is nothing to consume).
    while True:
        for token in tokens:
            spec = CONVERSION.fullmatch(token)
            out.append(printf_convert(spec, arguments.pop(0)) if spec else ESCAPES.get(token, token))
        if not arguments:
            break
    return "".join(out), "exact"


# --- seq --------------------------------------------------------------------------------------------

def seq_render(intent):
    numbers = [intent[k] for k in ("first", "step", "last") if k in intent]
    return ("seq" + (" -w" if intent.get("equal_width") else "")
            + (" -s " + quote(intent["separator"]) if "separator" in intent else "")
            + "".join(f" {n}" for n in numbers))


def seq_validation(intent):
    if "step" in intent and "first" not in intent:
        raise ValueError("seq step needs a first value")
    if intent.get("step", 1) < 1 or intent.get("first", 1) > intent["last"] or intent["last"] > 1000:
        raise ValueError("seq needs 1 <= step, first <= last <= 1000")
    if "separator" in intent and ("\\" in intent["separator"] or intent["separator"].startswith("-")
                                  or intent["separator"] == "\n"):
        raise ValueError("seq separator must not start with a dash or contain backslashes")


def seq_check(intent, ctx):
    values = list(range(intent.get("first", 1), intent["last"] + 1, intent.get("step", 1)))
    width = max(len(str(intent.get("first", 1))), len(str(intent["last"]))) if intent.get("equal_width") else 0
    return intent.get("separator", "\n").join(str(v).zfill(width) for v in values) + "\n", "exact"


# --- expr -------------------------------------------------------------------------------------------

EXPR_OPERATORS = "+|-|*|/|%|<|<=|=|!=|>=|>"
EXPR_TEXT = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.,:/@#-]*")


def expr_value(intent):
    """The text expr prints for this intent, computed in Python (None for a division by zero)."""
    if "length_of" in intent:
        return str(len(intent["length_of"]))
    if "substr_of" in intent:
        start = intent["start"]
        return intent["substr_of"][start - 1:start - 1 + intent["count"]]
    left, right = intent["left"], intent["right"]
    result = {"+": lambda: left + right, "-": lambda: left - right, "*": lambda: left * right,
              "/": lambda: left // right if right else None, "%": lambda: left % right if right else None,
              "<": lambda: int(left < right), "<=": lambda: int(left <= right), "=": lambda: int(left == right),
              "!=": lambda: int(left != right), ">=": lambda: int(left >= right), ">": lambda: int(left > right)}[intent["operator"]]()
    return None if result is None else str(result)


def expr_render(intent):
    if "length_of" in intent:
        return f"expr length {quote(intent['length_of'])}"
    if "substr_of" in intent:
        return f"expr substr {quote(intent['substr_of'])} {intent['start']} {intent['count']}"
    return f"expr {intent['left']} {quote(intent['operator'])} {intent['right']}"


def expr_validation(intent):
    if "operator" in intent:
        only(intent, ("left", "operator", "right"))
        if "left" not in intent or "right" not in intent:
            raise ValueError("expr arithmetic needs left and right")
    elif "length_of" in intent:
        only(intent, ("length_of",))
    elif "substr_of" in intent:
        only(intent, ("substr_of", "start", "count"))
        if intent.get("start", 0) < 1 or intent.get("count", 0) < 1:
            raise ValueError("expr substr needs start >= 1 and count >= 1")
    else:
        raise ValueError("expr needs an operator, length_of or substr_of")
    for name in ("length_of", "substr_of"):
        if name in intent and not EXPR_TEXT.fullmatch(intent[name]):
            raise ValueError(f"Unsupported expr text {intent[name]!r}")
    # expr exits with status 1 for a null or zero result and 2/3 for errors; this family only covers success.
    value = expr_value(intent)
    if value is None or re.fullmatch(r"-?0*", value):
        raise ValueError("expr needs a nonzero, nonempty result and a nonzero divisor")


def expr_check(intent, ctx):
    return expr_value(intent) + "\n", "exact"


# --- factor -----------------------------------------------------------------------------------------

def prime_factors(number):
    factors, divisor = [], 2
    while divisor * divisor <= number:
        while number % divisor == 0:
            factors.append(divisor)
            number //= divisor
        divisor += 1
    return factors + ([number] if number > 1 else [])


def factor_numbers(intent):
    return [intent["number"]] + intent.get("others", [])


def factor_validation(intent):
    if not all(2 <= n <= 10**9 for n in factor_numbers(intent)):
        raise ValueError("factor numbers must be between 2 and 10**9")


def factor_check(intent, ctx):
    return "".join(f"{n}: " + " ".join(map(str, prime_factors(n))) + "\n" for n in factor_numbers(intent)), "exact"


# --- test -------------------------------------------------------------------------------------------

TEST_FLAGS = {"file": "f", "directory": "d", "exists": "e", "nonempty": "s", "readable": "r", "writable": "w"}
TEST_STRINGS = {"string_equal": "=", "string_differs": "!="}
TEST_NUMBERS = {"number_eq": "-eq", "number_ne": "-ne", "number_lt": "-lt", "number_le": "-le", "number_gt": "-gt", "number_ge": "-ge"}
TEST_CONDITIONS = "|".join([*TEST_FLAGS, *TEST_STRINGS, *TEST_NUMBERS])


def test_render(intent):
    condition = intent["condition"]
    if condition in TEST_FLAGS:
        return f"test -{TEST_FLAGS[condition]} {quote(intent['target'])}"
    operator = TEST_STRINGS.get(condition) or TEST_NUMBERS[condition]
    return f"test {quote(intent['left'])} {operator} {quote(intent['right'])}"


def test_validation(intent):
    condition = intent["condition"]
    if condition in TEST_FLAGS:
        only(intent, ("condition", "target"))
        if "target" not in intent or intent["target"].startswith("-"):
            raise ValueError("file tests need a target that does not start with a dash")
        return
    only(intent, ("condition", "left", "right"))
    if "left" not in intent or "right" not in intent:
        raise ValueError("comparisons need left and right")
    for side in (intent["left"], intent["right"]):
        if condition in TEST_NUMBERS and not re.fullmatch(r"\d+", side):
            raise ValueError("numeric tests need decimal integers")
        if condition in TEST_STRINGS and (side[0] in "-!(" or side in ("=", "!=")):
            raise ValueError("string operands must not look like test operators")


def test_fixture(intent, seed, api):
    if intent["condition"] == "directory":
        api.directory(intent["target"])
    elif intent["condition"] in TEST_FLAGS:
        api.file(intent["target"], "some content\n")


def test_check(intent, ctx):
    # The observable result is exit status 0 (Spec.returncode), so the condition must hold; verify that from
    # the fixture's initial state or the operands themselves, never from the command.
    condition = intent["condition"]
    if condition in TEST_FLAGS:
        info = ctx.state.get(abspath(intent["target"]))
        holds = info is not None and {
            "file": info["type"] == "file",
            "directory": info["type"] == "directory",
            "exists": True,
            "nonempty": info["type"] == "file" and info["size"] > 0,
            "readable": bool(info["mode"] & 0o400),  # the container user owns the fixture files
            "writable": bool(info["mode"] & 0o200),
        }[condition]
    elif condition in TEST_STRINGS:
        holds = (intent["left"] == intent["right"]) == (condition == "string_equal")
    else:
        left, right = int(intent["left"]), int(intent["right"])
        holds = {"number_eq": left == right, "number_ne": left != right, "number_lt": left < right,
                 "number_le": left <= right, "number_gt": left > right, "number_ge": left >= right}[condition]
    if not holds:
        raise ValueError(f"Condition {condition} does not hold for {intent}")
    return "", "exact"


# --- yes --------------------------------------------------------------------------------------------

def yes_render(intent):
    return "yes " + (quote(intent["text"]) + " " if "text" in intent else "") + f"| head -n {intent['count']}"


def yes_validation(intent):
    text = intent.get("text")
    if text is not None and (text.startswith("-") or text == "y"):
        raise ValueError("yes text must not start with a dash; omit it for the default y")
    if not 1 <= intent["count"] <= 1000:
        raise ValueError("yes count must be 1..1000")


def yes_check(intent, ctx):
    return (intent.get("text", "y") + "\n") * intent["count"], "exact"


# --- sleep / timeout --------------------------------------------------------------------------------

def seconds_text(intent):
    """Whole seconds come from `seconds`, fractions from `duration`, so each wait has one spelling."""
    exactly_one(intent, "seconds", "duration")
    if "duration" in intent and not FRACTION.fullmatch(intent["duration"]):
        raise ValueError(f"duration must be a fraction such as 0.5, got {intent['duration']!r}")
    return intent["duration"] if "duration" in intent else str(intent["seconds"])


def sleep_validation(intent):
    if not 0 < float(seconds_text(intent)) <= 2:
        raise ValueError("sleep must last more than 0 and at most 2 seconds (3 second execution limit)")


def timeout_render(intent):
    command = f"tail -f {quote(intent['follow'])}" if "follow" in intent else f"sleep {intent['sleep_seconds']}"
    return "timeout" + (f" -s {intent['signal']}" if "signal" in intent else "") + f" {seconds_text(intent)} {command}"


def timeout_validation(intent):
    limit = float(seconds_text(intent))
    exactly_one(intent, "sleep_seconds", "follow")
    if not 0 < limit <= 2:
        raise ValueError("timeout limit must be above 0 and at most 2 seconds")
    if "sleep_seconds" in intent and not limit < intent["sleep_seconds"] <= 600:
        raise ValueError("the slept time must exceed the limit so the command is stopped")
    if "follow" in intent and (intent["follow"].startswith("-") or "\\" in intent["follow"]):
        raise ValueError("follow must be a plain file name")


def timeout_fixture(intent, seed, api):
    if "follow" in intent:
        api.file(intent["follow"])  # default generated lines, more than ten


def timeout_check(intent, ctx):
    # tail -f prints the last ten lines immediately and is then stopped at the limit (status 124).
    if "follow" in intent:
        return "".join(ctx.read(intent["follow"]).splitlines(keepends=True)[-10:]), "exact"
    return "", "exact"


# --- env / printenv ---------------------------------------------------------------------------------

def parse_assignments(assignments):
    pairs = []
    for text in assignments:
        name, separator, value = text.partition("=")
        if not separator or not VARIABLE_NAME.fullmatch(name) or name in RESERVED_VARIABLES or not value:
            raise ValueError(f"Unsupported assignment {text!r}")
        pairs.append((name, value))
    if len({name for name, _ in pairs}) != len(pairs):
        raise ValueError("assignment names must be distinct")
    return pairs


def env_validation(intent):
    if "unset" in intent:
        only(intent, ("unset",))
        if intent["unset"] not in CONTAINER_ENV:
            raise ValueError(f"Can only remove a variable the container sets, not {intent['unset']!r}")
        return
    if "assignments" not in intent:
        only(intent, ())
        return
    only(intent, ("assignments", "clean", "show"))
    names = {name for name, _ in parse_assignments(intent["assignments"])}
    if intent.get("clean"):
        if "show" in intent:
            raise ValueError("a clean environment is listed whole; show goes with a normal environment")
    elif "show" not in intent or not set(intent["show"]) <= names:
        raise ValueError("show must pick variables from the assignments")


def env_render(intent):
    """`env` lists the environment; otherwise env runs printenv in a modified environment."""
    if "unset" in intent:
        return f"env -u {intent['unset']} printenv"
    if "assignments" not in intent:
        return "env"
    assignments = " ".join(f"{name}={quote(value)}" for name, value in parse_assignments(intent["assignments"]))
    if intent.get("clean"):
        return f"env -i {assignments} printenv"
    return f"env {assignments} printenv " + " ".join(intent["show"])


def bookkeeping(ctx):
    """Values of the BOOKKEEPING variables: one of the listed choices when the output shows it, else the canonical
    one. These are the only details taken from the output; every other variable is computed."""
    values = {name: choices[0] for name, choices in BOOKKEEPING.items()}
    for line in ctx.outcome["stdout"].splitlines():
        name, _, value = line.partition("=")
        if name in BOOKKEEPING and value in BOOKKEEPING[name]:
            values[name] = value
    return values


def env_check(intent, ctx):
    inherited = {**CONTAINER_ENV, **SHELL_ENV, **bookkeeping(ctx)}
    if "unset" in intent:
        return env_lines({k: v for k, v in inherited.items() if k != intent["unset"]}), "lines"
    if "assignments" not in intent:
        return env_lines(inherited), "lines"
    pairs = dict(parse_assignments(intent["assignments"]))
    if intent.get("clean"):
        return env_lines(pairs), "lines"
    return "".join(pairs[name] + "\n" for name in intent["show"]), "exact"


def printenv_validation(intent):
    unknown = set(intent["names"]) - set(CONTAINER_ENV)
    if unknown:
        raise ValueError(f"printenv names must be variables the container sets: {sorted(unknown)}")


def printenv_check(intent, ctx):
    return "".join(CONTAINER_ENV[name] + "\n" for name in intent["names"]), "exact"


# --- whoami / id / groups ---------------------------------------------------------------------------

def whoami_check(intent, ctx):
    return CONTAINER_USER + "\n", "exact"


def other_user_validation(intent):
    # Naming the current user would only duplicate the plain form, so `user` is for other accounts.
    if "user" in intent and (intent["user"] not in USERS or intent["user"] == CONTAINER_USER):
        raise ValueError(f"user must be another known account, not {intent['user']!r}")


def id_render(intent):
    return "id" + (f" -{intent['option']}" if "option" in intent else "") + (f" {intent['user']}" if "user" in intent else "")


def id_check(intent, ctx):
    name = intent.get("user", CONTAINER_USER)
    info = USERS[name]
    option = intent.get("option")
    if option == "u":
        return f"{info['uid']}\n", "exact"
    if option == "g":
        return f"{info['gid']}\n", "exact"
    if option == "G":
        return " ".join(str(gid) for gid, _ in info["groups"]) + "\n", "exact"
    groups = ",".join(f"{gid}({gname})" for gid, gname in info["groups"])
    return f"uid={info['uid']}({name}) gid={info['gid']}({info['groups'][0][1]}) groups={groups}\n", "exact"


def groups_check(intent, ctx):
    names = " ".join(gname for _, gname in USERS[intent.get("user", CONTAINER_USER)]["groups"])
    return (f"{intent['user']} : {names}" if "user" in intent else names) + "\n", "exact"


SPECS = {
    "echo": Spec({"text": "text", "no_newline": "bool"}, frozenset({"text"}),
                 echo_render, no_fixture, echo_check, extra_validation=echo_validation),
    "printf": Spec({"format": "text", "arguments": "paths"}, frozenset({"format"}),
                   printf_render, no_fixture, printf_check, extra_validation=printf_validation),
    "seq": Spec({"first": "int", "step": "int", "last": "int", "equal_width": "bool", "separator": "text"}, frozenset({"last"}),
                seq_render, no_fixture, seq_check, extra_validation=seq_validation),
    "expr": Spec({"left": "int", "operator": "enum:" + EXPR_OPERATORS, "right": "int", "length_of": "text",
                  "substr_of": "text", "start": "int", "count": "int"}, frozenset(),
                 expr_render, no_fixture, expr_check, extra_validation=expr_validation),
    "factor": Spec({"number": "int", "others": "intlist"}, frozenset({"number"}),
                   lambda intent: "factor " + " ".join(map(str, factor_numbers(intent))), no_fixture, factor_check,
                   extra_validation=factor_validation),
    "true": Spec({}, frozenset(), lambda intent: "true", no_fixture, silent_check),
    "false": Spec({}, frozenset(), lambda intent: "false", no_fixture, silent_check, returncode=1),
    "test": Spec({"condition": "enum:" + TEST_CONDITIONS, "target": "path", "left": "text", "right": "text"}, frozenset({"condition"}),
                 test_render, test_fixture, test_check, extra_validation=test_validation),
    "yes": Spec({"text": "text", "count": "int"}, frozenset({"count"}),
                yes_render, no_fixture, yes_check, extra_validation=yes_validation),
    "sleep": Spec({"seconds": "int", "duration": "text"}, frozenset(),
                  lambda intent: "sleep " + seconds_text(intent), no_fixture, silent_check, extra_validation=sleep_validation),
    "timeout": Spec({"seconds": "int", "duration": "text", "sleep_seconds": "int", "follow": "path", "signal": "enum:HUP|INT|TERM"},
                    frozenset(), timeout_render, timeout_fixture, timeout_check, returncode=124,
                    extra_validation=timeout_validation),
    "env": Spec({"assignments": "paths", "clean": "bool", "show": "paths", "unset": "text"}, frozenset(),
                env_render, no_fixture, env_check, extra_validation=env_validation),
    "printenv": Spec({"names": "paths"}, frozenset({"names"}), lambda intent: "printenv " + " ".join(intent["names"]),
                     no_fixture, printenv_check, extra_validation=printenv_validation),
    "whoami": Spec({}, frozenset(), lambda intent: "whoami", no_fixture, whoami_check),
    "id": Spec({"option": "enum:u|g|G", "user": "text"}, frozenset(),
               id_render, no_fixture, id_check, extra_validation=other_user_validation),
    "groups": Spec({"user": "text"}, frozenset(), lambda intent: "groups" + (f" {intent['user']}" if "user" in intent else ""),
                   no_fixture, groups_check, extra_validation=other_user_validation),
}
