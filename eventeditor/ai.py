import aamp
import byml
from enum import IntEnum
import functools
import os
from pathlib import Path
import typing
import wszst_yaz0

_rom_path: typing.Optional[Path] = None
def set_rom_path(p: typing.Optional[str]) -> None:
    if p:
        global _rom_path
        _rom_path = Path(p)

def _list_aiprog_files(path: Path):
    try:
        return path.glob('*.baiprog')
    except:
        return []

class AIProg:
    def __init__(self) -> None:
        self.actions: typing.Dict[str, str] = dict()
        self.queries: typing.Dict[str, str] = dict()

    def load_actor_aiprog(self, actor_name: str) -> bool:
        if not _rom_path:
            return False

        rel_roots = (
            '',
            'Pack/Bootup.pack/',
            'Pack/TitleBG.pack/',
            'Pack/RemainsWind.pack/',
            'Pack/RemainsElectric.pack/',
            'Pack/RemainsWater.pack/',
            'Pack/RemainsFire.pack/',
        )

        for rel_root in rel_roots:
            root = _rom_path / rel_root
            aiprog_dir = root/'Actor'/'Pack'/f'{actor_name}.sbactorpack'/'Actor'/'AIProgram'
            for path in _list_aiprog_files(aiprog_dir):
                with open(path, 'rb') as aiprog:
                    pio = aamp.Reader(aiprog.read()).parse()
                if self._do_load_actor_aiprog(pio):
                    return True

        return False

    def _do_load_actor_aiprog(self, aiprog: aamp.ParameterIO) -> bool:
        try:
            param_root = aiprog.list('param_root')
            action_list = param_root.list('Action')
            query_list = param_root.list('Query')

            for i in range(len(action_list.lists)):
                definition = action_list.list(f'Action_{i}').object('Def')
                class_name = definition.param('ClassName')
                try:
                    name = definition.param('Name')
                except KeyError:
                    name = class_name
                self.actions[name] = class_name

            for i in range(len(query_list.lists)):
                definition = query_list.list(f'Query_{i}').object('Def')
                class_name = definition.param('ClassName')
                try:
                    name = definition.param('Name')
                except KeyError:
                    name = class_name
                self.queries[name] = class_name

            return True

        except KeyError:
            return False

@functools.lru_cache(maxsize=50)
def load_aiprog(actor_name: str) -> typing.Optional[AIProg]:
    aiprog = AIProg()
    if not aiprog.load_actor_aiprog(actor_name):
        return None
    return aiprog

class AIType(IntEnum):
    Action = 0
    Query = 1

class AIParameter(typing.NamedTuple):
    name: str
    type: str
    default_value: typing.Any

    def get_default_value(self) -> typing.Any:
        if self.default_value is not None:
            return self.default_value
        if self.type == 'Bool':
            return False
        if self.type == 'Int':
            return 0
        if self.type == 'String':
            return ''
        if self.type == 'Float':
            return 0.0
        if self.type == 'Vec3':
            return [0.0, 0.0, 0.0]
        if self.type == 'AITreeVariablePointer' \
        or self.type == 'MesTransceiverId' \
        or self.type == 'BaseProcHandle' \
        or self.type == 'Actor':
            # These shouldn't ever appear in actions/queries.
            return None
        return '???'

class AIDef:
    def __init__(self) -> None:
        self._ai_defs: dict = dict()

    def _init_ai_defs(self) -> None:
        if self._ai_defs or not _rom_path:
            return

        raw_data = wszst_yaz0.decompress_file(
            str(_rom_path / 'Pack/Bootup.pack/Actor/AIDef/AIDef_Game.product.sbyml'))
        defs = byml.Byml(raw_data).parse()
        if isinstance(defs, dict):
            self._ai_defs = defs

    def get_parameters(self, ai_type: AIType, name: str) -> typing.List[AIParameter]:
        self._init_ai_defs()
        if not self._ai_defs:
            return []

        def map_to_ai_param(entry: dict) -> AIParameter:
            # {Name: XXXXX, Type: Int}
            # {Name: XXXXX, Type: Int, Value: 0}
            return AIParameter(name=entry['Name'], type=entry['Type'],
                default_value=entry.get('Value', None))

        try:
            if ai_type == AIType.Action:
                return [map_to_ai_param(x) for x in self._ai_defs['Actions'][name]['DynamicInstParams']]
            if ai_type == AIType.Query:
                return [map_to_ai_param(x) for x in self._ai_defs['Querys'][name]['DynamicInstParams']]
            return []
        except:
            return []

ai_def_instance = AIDef()
