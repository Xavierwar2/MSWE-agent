from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from sweagent.agent.models import ModelArguments, OpenAIModel, TogetherModel


@pytest.fixture()
def openai_mock_client():
    model = Mock()
    response = Mock()
    choice = Mock()
    choice.message.content = "test"
    response.choices = [choice]
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 10
    model.chat.completions.create = MagicMock(return_value=response)

    return model


@pytest.fixture()
def mock_together_response():
    return {
        "choices": [{"text": "<human>Hello</human>"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }


TEST_HISTORY = [{"role": "system", "content": "Hello, how are you?"}]


def test_openai_model(openai_mock_client):
    for model_name in list(OpenAIModel.MODELS) + list(OpenAIModel.SHORTCUTS):
        TEST_MODEL_ARGUMENTS = ModelArguments(model_name)
        with patch("sweagent.agent.models.keys_config"), patch("sweagent.agent.models.OpenAI"):
            model = OpenAIModel(TEST_MODEL_ARGUMENTS, [])
        model.client = openai_mock_client
        model.query(TEST_HISTORY)


def test_openai_model_accepts_string_response(openai_mock_client):
    TEST_MODEL_ARGUMENTS = ModelArguments("gpt-5.4")
    with patch("sweagent.agent.models.keys_config"), patch("sweagent.agent.models.OpenAI"):
        model = OpenAIModel(TEST_MODEL_ARGUMENTS, [])
    openai_mock_client.chat.completions.create.return_value = "test"
    model.client = openai_mock_client

    assert model.query(TEST_HISTORY) == "test"
    assert model.stats.api_calls == 1
    assert model.stats.tokens_sent == 0
    assert model.stats.tokens_received == 0


def test_openai_model_accepts_dict_response(openai_mock_client):
    TEST_MODEL_ARGUMENTS = ModelArguments("gpt-5.4")
    with patch("sweagent.agent.models.keys_config"), patch("sweagent.agent.models.OpenAI"):
        model = OpenAIModel(TEST_MODEL_ARGUMENTS, [])
    openai_mock_client.chat.completions.create.return_value = {
        "choices": [{"message": {"content": "test"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    model.client = openai_mock_client

    assert model.query(TEST_HISTORY) == "test"
    assert model.stats.api_calls == 1
    assert model.stats.tokens_sent == 10
    assert model.stats.tokens_received == 5


@pytest.mark.parametrize("model_name", list(TogetherModel.MODELS) + list(TogetherModel.SHORTCUTS))
def test_together_model(mock_together_response, model_name):
    with patch("sweagent.agent.models.keys_config"), patch("sweagent.agent.models.together") as mock_together:
        mock_together.version = "1.1.0"
        mock_together.Complete.create.return_value = mock_together_response

        model_args = ModelArguments(model_name)
        model = TogetherModel(model_args, [])
        model.query(TEST_HISTORY)
