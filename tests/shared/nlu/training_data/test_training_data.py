from typing import Text, List

import pytest

import rasa.shared.utils.io
from rasa.shared.core.constants import USER_INTENT_OUT_OF_SCOPE
from rasa.shared.nlu.constants import TEXT, INTENT_RESPONSE_KEY
from rasa.nlu.convert import convert_training_data
from rasa.nlu.extractors.mitie_entity_extractor import MitieEntityExtractor
from rasa.nlu.tokenizers.whitespace_tokenizer import WhitespaceTokenizer
from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.shared.nlu.training_data.loading import guess_format, UNK, load_data
from rasa.shared.nlu.training_data.util import (
    get_file_format_extension,
    template_key_to_intent_response_key,
    intent_response_key_to_template_key,
)

import rasa.shared.data


def test_luis_data():
    td = load_data("data/examples/luis/demo-restaurants_v5.json")

    assert not td.is_empty()
    assert len(td.entity_examples) == 8
    assert len(td.intent_examples) == 28
    assert len(td.training_examples) == 28
    assert td.entity_synonyms == {}
    assert td.intents == {"affirm", "goodbye", "greet", "inform"}
    assert td.entities == {"location", "cuisine"}


def test_wit_data():
    td = load_data("data/examples/wit/demo-flights.json")
    assert not td.is_empty()
    assert len(td.entity_examples) == 4
    assert len(td.intent_examples) == 5
    assert len(td.training_examples) == 5
    assert td.entity_synonyms == {}
    assert td.intents == {"flight_booking", USER_INTENT_OUT_OF_SCOPE}
    assert td.entities == {"location", "wit$datetime"}


def test_dialogflow_data():
    td = load_data("data/examples/dialogflow/")
    assert not td.is_empty()
    assert len(td.entity_examples) == 5
    assert len(td.intent_examples) == 24
    assert len(td.training_examples) == 24
    assert len(td.lookup_tables) == 2
    assert td.intents == {"affirm", "goodbye", "hi", "inform"}
    assert td.entities == {"cuisine", "location"}
    non_trivial_synonyms = {k: v for k, v in td.entity_synonyms.items() if k != v}
    assert non_trivial_synonyms == {
        "mexico": "mexican",
        "china": "chinese",
        "india": "indian",
    }
    # The order changes based on different computers hence the grouping
    assert {td.lookup_tables[0]["name"], td.lookup_tables[1]["name"]} == {
        "location",
        "cuisine",
    }
    assert {
        len(td.lookup_tables[0]["elements"]),
        len(td.lookup_tables[1]["elements"]),
    } == {4, 6}


def test_lookup_table_json():
    lookup_fname = "data/test/lookup_tables/plates.txt"
    td_lookup = load_data("data/test/lookup_tables/lookup_table.json")
    assert not td_lookup.is_empty()
    assert len(td_lookup.lookup_tables) == 1
    assert td_lookup.lookup_tables[0]["name"] == "plates"
    assert td_lookup.lookup_tables[0]["elements"] == lookup_fname


def test_lookup_table_md():
    lookup_fname = "data/test/lookup_tables/plates.txt"
    td_lookup = load_data("data/test/lookup_tables/lookup_table.md")
    assert not td_lookup.is_empty()
    assert len(td_lookup.lookup_tables) == 1
    assert td_lookup.lookup_tables[0]["name"] == "plates"
    assert td_lookup.lookup_tables[0]["elements"] == lookup_fname


def test_composite_entities_data():
    td = load_data("data/test/demo-rasa-composite-entities.md")
    assert not td.is_empty()
    assert len(td.entity_examples) == 11
    assert len(td.intent_examples) == 45
    assert len(td.training_examples) == 45
    assert td.entity_synonyms == {"SF": "San Fransisco"}
    assert td.intents == {
        "order_pizza",
        "book_flight",
        "chitchat",
        "greet",
        "goodbye",
        "affirm",
    }
    assert td.entities == {"location", "topping", "size"}
    assert td.entity_groups == {"1", "2"}
    assert td.entity_roles == {"to", "from"}
    assert td.number_of_examples_per_entity["entity 'location'"] == 8
    assert td.number_of_examples_per_entity["group '1'"] == 9
    assert td.number_of_examples_per_entity["role 'from'"] == 3


def test_intent_response_key_to_template_key():
    intent_response_key = "chitchat/ask_name"
    template_key = "utter_chitchat/ask_name"
    assert intent_response_key_to_template_key(intent_response_key) == template_key


def test_template_key_to_intent_response_key():
    intent_response_key = "chitchat/ask_name"
    template_key = "utter_chitchat/ask_name"
    assert template_key_to_intent_response_key(template_key) == intent_response_key


@pytest.mark.parametrize(
    "files",
    [
        [
            "data/examples/rasa/demo-rasa.json",
            "data/examples/rasa/demo-rasa-responses.md",
        ],
        [
            "data/examples/rasa/demo-rasa.md",
            "data/examples/rasa/demo-rasa-responses.md",
        ],
    ],
)
def test_demo_data(files: List[Text]):
    from rasa.shared.importers.utils import training_data_from_paths

    trainingdata = training_data_from_paths(files, language="en")
    assert trainingdata.intents == {
        "affirm",
        "greet",
        "restaurant_search",
        "goodbye",
        "chitchat",
    }
    assert trainingdata.entities == {"location", "cuisine"}
    assert set(trainingdata.responses.keys()) == {
        "utter_chitchat/ask_name",
        "utter_chitchat/ask_weather",
    }
    assert len(trainingdata.training_examples) == 46
    assert len(trainingdata.intent_examples) == 46
    assert len(trainingdata.response_examples) == 4
    assert len(trainingdata.entity_examples) == 11
    assert len(trainingdata.responses) == 2

    assert trainingdata.entity_synonyms == {
        "Chines": "chinese",
        "Chinese": "chinese",
        "chines": "chinese",
        "vegg": "vegetarian",
        "veggie": "vegetarian",
    }

    assert trainingdata.regex_features == [
        {"name": "greet", "pattern": r"hey[^\s]*"},
        {"name": "zipcode", "pattern": r"[0-9]{5}"},
    ]


@pytest.mark.parametrize(
    "files",
    [
        [
            "data/examples/rasa/demo-rasa.json",
            "data/examples/rasa/demo-rasa-responses.md",
        ],
        [
            "data/examples/rasa/demo-rasa.md",
            "data/examples/rasa/demo-rasa-responses.md",
        ],
    ],
)
def test_demo_data_filter_out_retrieval_intents(files):
    from rasa.shared.importers.utils import training_data_from_paths

    training_data = training_data_from_paths(files, language="en")
    assert len(training_data.training_examples) == 46

    training_data_filtered = training_data.filter_training_examples(
        lambda ex: ex.get(INTENT_RESPONSE_KEY) is None
    )
    assert len(training_data_filtered.training_examples) == 42

    training_data_filtered_2 = training_data.filter_training_examples(
        lambda ex: ex.get(INTENT_RESPONSE_KEY) is not None
    )
    assert len(training_data_filtered_2.training_examples) == 4

    # make sure filtering operation doesn't mutate the source training data
    assert len(training_data.training_examples) == 46


@pytest.mark.parametrize(
    "filepaths",
    [["data/examples/rasa/demo-rasa.md", "data/examples/rasa/demo-rasa-responses.md"]],
)
def test_train_test_split(filepaths: List[Text]):
    from rasa.shared.importers.utils import training_data_from_paths

    training_data = training_data_from_paths(filepaths, language="en")

    assert training_data.intents == {
        "affirm",
        "greet",
        "restaurant_search",
        "goodbye",
        "chitchat",
    }
    assert training_data.entities == {"location", "cuisine"}
    assert set(training_data.responses.keys()) == {
        "utter_chitchat/ask_name",
        "utter_chitchat/ask_weather",
    }

    NUM_TRAIN_EXAMPLES = 46
    NUM_RESPONSE_EXAMPLES = 4

    assert len(training_data.training_examples) == NUM_TRAIN_EXAMPLES
    assert len(training_data.intent_examples) == NUM_TRAIN_EXAMPLES
    assert len(training_data.response_examples) == NUM_RESPONSE_EXAMPLES

    for train_percent in range(50, 95, 5):
        train_frac = train_percent / 100.0
        train_split, test_split = training_data.train_test_split(train_frac)

        assert (
            len(test_split.training_examples) + len(train_split.training_examples)
            == NUM_TRAIN_EXAMPLES
        )

        num_classes = (
            len(training_data.number_of_examples_per_intent.keys())
            + -len(training_data.retrieval_intents)
            + len(training_data.number_of_examples_per_response)
        )

        expected_num_train_examples_floor = int(train_frac * NUM_TRAIN_EXAMPLES)
        if NUM_TRAIN_EXAMPLES - expected_num_train_examples_floor < num_classes:
            expected_num_train_examples_floor = NUM_TRAIN_EXAMPLES - num_classes - 1

        assert len(train_split.training_examples) >= expected_num_train_examples_floor
        assert (
            len(train_split.training_examples) <= expected_num_train_examples_floor + 1
        )

        assert len(training_data.number_of_examples_per_intent.keys()) == len(
            test_split.number_of_examples_per_intent.keys()
        )
        assert len(training_data.number_of_examples_per_intent.keys()) == len(
            train_split.number_of_examples_per_intent.keys()
        )
        assert len(training_data.number_of_examples_per_response.keys()) == len(
            train_split.number_of_examples_per_response.keys()
        )
        assert len(training_data.number_of_examples_per_response.keys()) == len(
            train_split.number_of_examples_per_response.keys()
        )


@pytest.mark.parametrize(
    "filepaths",
    [["data/examples/rasa/demo-rasa.md", "data/examples/rasa/demo-rasa-responses.md"]],
)
def test_train_test_split_with_random_seed(filepaths):
    from rasa.shared.importers.utils import training_data_from_paths

    td = training_data_from_paths(filepaths, language="en")

    td_train_1, td_test_1 = td.train_test_split(train_frac=0.8, random_seed=1)
    td_train_2, td_test_2 = td.train_test_split(train_frac=0.8, random_seed=1)
    train_1_intent_examples = [e.get(TEXT) for e in td_train_1.intent_examples]
    train_2_intent_examples = [e.get(TEXT) for e in td_train_2.intent_examples]

    test_1_intent_examples = [e.get(TEXT) for e in td_test_1.intent_examples]
    test_2_intent_examples = [e.get(TEXT) for e in td_test_2.intent_examples]

    assert train_1_intent_examples == train_2_intent_examples
    assert test_1_intent_examples == test_2_intent_examples


@pytest.mark.parametrize(
    "files",
    [
        ("data/examples/rasa/demo-rasa.json", "data/test/multiple_files_json"),
        ("data/examples/rasa/demo-rasa.md", "data/test/multiple_files_markdown"),
        ("data/examples/rasa/demo-rasa.md", "data/test/duplicate_intents_markdown"),
    ],
)
def test_data_merging(files):
    td_reference = load_data(files[0])
    td = load_data(files[1])
    assert len(td.entity_examples) == len(td_reference.entity_examples)
    assert len(td.intent_examples) == len(td_reference.intent_examples)
    assert len(td.training_examples) == len(td_reference.training_examples)
    assert td.intents == td_reference.intents
    assert td.entities == td_reference.entities
    assert td.entity_synonyms == td_reference.entity_synonyms
    assert td.regex_features == td_reference.regex_features


def test_markdown_single_sections():
    td_regex_only = load_data("data/test/markdown_single_sections/regex_only.md")
    assert td_regex_only.regex_features == [{"name": "greet", "pattern": r"hey[^\s]*"}]

    td_syn_only = load_data("data/test/markdown_single_sections/synonyms_only.md")
    assert td_syn_only.entity_synonyms == {"Chines": "chinese", "Chinese": "chinese"}


def test_repeated_entities(tmp_path):
    data = """
{
  "rasa_nlu_data": {
    "common_examples" : [
      {
        "text": "book a table today from 3 to 6 for 3 people",
        "intent": "unk",
        "entities": [
          {
            "entity": "description",
            "start": 35,
            "end": 36,
            "value": "3"
          }
        ]
      }
    ]
  }
}"""
    f = tmp_path / "tmp_training_data.json"
    f.write_text(data, rasa.shared.utils.io.DEFAULT_ENCODING)
    td = load_data(str(f))
    assert len(td.entity_examples) == 1
    example = td.entity_examples[0]
    entities = example.get("entities")
    assert len(entities) == 1
    tokens = WhitespaceTokenizer().tokenize(example, attribute=TEXT)
    start, end = MitieEntityExtractor.find_entity(
        entities[0], example.get(TEXT), tokens
    )
    assert start == 9
    assert end == 10


def test_multiword_entities(tmp_path):
    data = """
{
  "rasa_nlu_data": {
    "common_examples" : [
      {
        "text": "show me flights to New York City",
        "intent": "unk",
        "entities": [
          {
            "entity": "destination",
            "start": 19,
            "end": 32,
            "value": "New York City"
          }
        ]
      }
    ]
  }
}"""
    f = tmp_path / "tmp_training_data.json"
    f.write_text(data, rasa.shared.utils.io.DEFAULT_ENCODING)
    td = load_data(str(f))
    assert len(td.entity_examples) == 1
    example = td.entity_examples[0]
    entities = example.get("entities")
    assert len(entities) == 1
    tokens = WhitespaceTokenizer().tokenize(example, attribute=TEXT)
    start, end = MitieEntityExtractor.find_entity(
        entities[0], example.get(TEXT), tokens
    )
    assert start == 4
    assert end == 7


def test_nonascii_entities(tmp_path):
    data = """
{
  "luis_schema_version": "5.0",
  "utterances" : [
    {
      "text": "I am looking for a ßäæ ?€ö) item",
      "intent": "unk",
      "entities": [
        {
          "entity": "description",
          "startPos": 19,
          "endPos": 26
        }
      ]
    }
  ]
}"""
    f = tmp_path / "tmp_training_data.json"
    f.write_text(data, rasa.shared.utils.io.DEFAULT_ENCODING)
    td = load_data(str(f))
    assert len(td.entity_examples) == 1
    example = td.entity_examples[0]
    entities = example.get("entities")
    assert len(entities) == 1
    entity = entities[0]
    assert entity["value"] == "ßäæ ?€ö)"
    assert entity["start"] == 19
    assert entity["end"] == 27
    assert entity["entity"] == "description"


def test_entities_synonyms(tmp_path):
    data = """
{
  "rasa_nlu_data": {
    "entity_synonyms": [
      {
        "value": "nyc",
        "synonyms": ["New York City", "nyc", "the big apple"]
      }
    ],
    "common_examples" : [
      {
        "text": "show me flights to New York City",
        "intent": "unk",
        "entities": [
          {
            "entity": "destination",
            "start": 19,
            "end": 32,
            "value": "NYC"
          }
        ]
      },
      {
        "text": "show me flights to nyc",
        "intent": "unk",
        "entities": [
          {
            "entity": "destination",
            "start": 19,
            "end": 22,
            "value": "nyc"
          }
        ]
      }
    ]
  }
}"""
    f = tmp_path / "tmp_training_data.json"
    f.write_text(data, rasa.shared.utils.io.DEFAULT_ENCODING)
    td = load_data(str(f))
    assert td.entity_synonyms["New York City"] == "nyc"


def cmp_message_list(firsts, seconds):
    assert len(firsts) == len(seconds), "Message lists have unequal length"


def cmp_dict_list(firsts, seconds):
    if len(firsts) != len(seconds):
        return False

    for a in firsts:
        for idx, b in enumerate(seconds):
            if hash(a) == hash(b):
                del seconds[idx]
                break
        else:
            others = ", ".join(e.text for e in seconds)
            assert False, f"Failed to find message {a.text} in {others}"
    return not seconds


@pytest.mark.parametrize(
    "data_file,gold_standard_file,output_format,language",
    [
        (
            "data/examples/wit/demo-flights.json",
            "data/test/wit_converted_to_rasa.json",
            "json",
            None,
        ),
        (
            "data/examples/luis/demo-restaurants_v5.json",
            "data/test/luis_converted_to_rasa.json",
            "json",
            None,
        ),
        (
            "data/examples/dialogflow/",
            "data/test/dialogflow_en_converted_to_rasa.json",
            "json",
            "en",
        ),
        (
            "data/examples/dialogflow/",
            "data/test/dialogflow_es_converted_to_rasa.json",
            "json",
            "es",
        ),
        (
            "data/examples/rasa/demo-rasa.md",
            "data/test/md_converted_to_json.json",
            "json",
            None,
        ),
        (
            "data/examples/rasa/demo-rasa.json",
            "data/test/json_converted_to_md.md",
            "md",
            None,
        ),
        (
            "data/test/training_data_containing_special_chars.json",
            "data/test/json_with_special_chars_convered_to_md.md",
            "md",
            None,
        ),
    ],
)
def test_training_data_conversion(
    tmpdir, data_file, gold_standard_file, output_format, language
):
    out_path = tmpdir.join("rasa_nlu_data.json")
    convert_training_data(data_file, out_path.strpath, output_format, language)
    td = load_data(out_path.strpath, language)
    assert td.entity_examples != []
    assert td.intent_examples != []

    gold_standard = load_data(gold_standard_file, language)
    cmp_message_list(td.entity_examples, gold_standard.entity_examples)
    cmp_message_list(td.intent_examples, gold_standard.intent_examples)
    assert td.entity_synonyms == gold_standard.entity_synonyms

    # converting the converted file back to original
    # file format and performing the same tests
    rto_path = tmpdir.join("data_in_original_format.txt")
    convert_training_data(out_path.strpath, rto_path.strpath, "json", language)
    rto = load_data(rto_path.strpath, language)
    cmp_message_list(gold_standard.entity_examples, rto.entity_examples)
    cmp_message_list(gold_standard.intent_examples, rto.intent_examples)
    assert gold_standard.entity_synonyms == rto.entity_synonyms

    # If the above assert fails - this can be used
    # to dump to the file and diff using git
    # with io.open(gold_standard_file) as f:
    #     f.write(td.as_json(indent=2))


@pytest.mark.parametrize(
    "data_file,expected_format",
    [
        (
            "data/examples/luis/demo-restaurants_v5.json",
            rasa.shared.data.yaml_file_extension(),
        ),
        ("data/examples", rasa.shared.data.yaml_file_extension()),
        ("data/examples/rasa/demo-rasa.md", rasa.shared.data.markdown_file_extension()),
        ("data/rasa_yaml_examples", rasa.shared.data.yaml_file_extension()),
    ],
)
def test_get_supported_file_format(data_file: Text, expected_format: Text):
    fformat = get_file_format_extension(data_file)
    assert fformat == expected_format


@pytest.mark.parametrize("data_file", ["path-does-not-exists", None])
def test_get_non_existing_file_format_raises(data_file: Text):
    with pytest.raises(AttributeError):
        get_file_format_extension(data_file)


def test_guess_format_from_non_existing_file_path():
    assert guess_format("not existing path") == UNK


def test_is_empty():
    assert TrainingData().is_empty()


def test_custom_attributes(tmp_path):
    data = """
{
  "rasa_nlu_data": {
    "common_examples" : [
      {
        "intent": "happy",
        "text": "I'm happy.",
        "sentiment": 0.8
      }
    ]
  }
}"""
    f = tmp_path / "tmp_training_data.json"
    f.write_text(data, rasa.shared.utils.io.DEFAULT_ENCODING)
    td = load_data(str(f))
    assert len(td.training_examples) == 1
    example = td.training_examples[0]
    assert example.get("sentiment") == 0.8
