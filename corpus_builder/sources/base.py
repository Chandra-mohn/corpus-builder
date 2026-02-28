
from abc import ABC, abstractmethod
from typing import Iterable, Dict

class SourceAdapter(ABC):
    @abstractmethod
    def discover_repositories(self) -> Iterable[Dict]:
        '''
        Must yield:
        {
            "id": stable_id,
            "clone_url": str,
            "vcs": "git" | "svn",
            "source": "github" | ...
        }
        '''
        pass
