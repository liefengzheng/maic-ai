# Runtime Skills

Each local Skill lives at `skills/<handler>/skill.py`. The handler directory name
must match `^[a-z][a-z0-9_]{0,99}$`, and `skill.py` must export a `Skill` class
with an asynchronous `execute(**kwargs)` method.

```python
from typing import Any

from app.runtime.skills import Skill as BaseSkill


class Skill(BaseSkill):
    async def execute(self, **kwargs: Any) -> Any:
        city = kwargs["city"]
        return {"city": city}
```

Names, descriptions, input/output schemas, versions, and execution settings are
stored in `skill_registry`. No manifest file is read at runtime.