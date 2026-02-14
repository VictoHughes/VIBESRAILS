"""Safe YAML loader with alias expansion limit (billion laughs protection).

Limits alias references to 100 to prevent exponential expansion attacks
where a small YAML file (1KB) can expand to gigabytes of memory.
"""

from __future__ import annotations

import yaml


def safe_yaml_load(stream):
    """yaml.safe_load replacement with alias bomb protection."""
    class _Loader(yaml.SafeLoader):
        def compose_node(self, parent, index):
            if self.check_event(yaml.AliasEvent):
                count = getattr(self, '_alias_count', 0) + 1
                if count > 100:
                    raise yaml.YAMLError("YAML alias limit exceeded (max 100)")
                self._alias_count = count
            return super().compose_node(parent, index)
    return yaml.load(stream, Loader=_Loader)
