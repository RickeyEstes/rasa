from typing import Any, Dict, Text

from rasa.nlu.emulators.no_emulator import NoEmulator
from rasa.shared.nlu.constants import (
    ENTITIES,
    ENTITY_ATTRIBUTE_TYPE,
    ENTITY_ATTRIBUTE_ROLE,
    ENTITY_ATTRIBUTE_VALUE,
    ENTITY_ATTRIBUTE_END,
    ENTITY_ATTRIBUTE_START,
    INTENT_RANKING_KEY,
    TEXT,
    INTENT,
    INTENT_NAME_KEY, PREDICTED_CONFIDENCE_KEY)
from typing import List, Optional


class LUISEmulator(NoEmulator):
    def __init__(self) -> None:
        """Emulates the response format of the LUIS Endpoint API v3.0 /predict endpoint:
        https://westcentralus.dev.cognitive.microsoft.com/docs/services/luis-endpoint-api-v3-0/"""

        super().__init__()
        self.name = "luis"

    def _top_intent(self, data) -> Optional[Dict[Text, Any]]:
        intent = data.get(INTENT)

        if not intent:
            return None

        return {
            "intent": intent[INTENT_NAME_KEY],
            "score": intent[PREDICTED_CONFIDENCE_KEY],
        }

    def _intents(self, data) -> List[Dict[Text, Any]]:
        if data.get(INTENT_RANKING_KEY):
            return [
                {"intent": el[INTENT_NAME_KEY], "score": el[PREDICTED_CONFIDENCE_KEY]}
                for el in data[INTENT_RANKING_KEY]
            ]
        else:
            top = self._top_intent(data)
            return [top] if top else []

    def normalise_response_json(self, data: Dict[Text, Any]) -> Dict[Text, Any]:
        """Transform data to luis.ai format."""

        return {
            "query": data[TEXT],
            "prediction": {
                "topIntent": self._top_intent(data),
                "intents": self._intents(data),
                "entities": [
                    {
                        "entity": e[ENTITY_ATTRIBUTE_VALUE],
                        "type": e[ENTITY_ATTRIBUTE_TYPE],
                        "startIndex": e.get(ENTITY_ATTRIBUTE_START),
                        "endIndex": (e[ENTITY_ATTRIBUTE_END] - 1) if ENTITY_ATTRIBUTE_END in e else None,
                        "score": e.get(PREDICTED_CONFIDENCE_KEY),
                        "role": e.get(ENTITY_ATTRIBUTE_ROLE)
                    }
                    for e in data[ENTITIES]
                ]
                if ENTITIES in data
                else [],
            },
        }
