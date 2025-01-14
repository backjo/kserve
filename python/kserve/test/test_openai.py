# Copyright 2023 The KServe Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from typing import AsyncIterator, Iterable, List, Tuple, Union

import pytest
from kserve.protocol.rest.openai import (
    ChatCompletionRequestMessage,
    ChatPrompt,
    CompletionRequest,
    ChatCompletionRequest,
    OpenAIChatAdapterModel,
)
from kserve.protocol.rest.openai.types.openapi import (
    CreateCompletionRequest,
    CreateChatCompletionRequest,
    CreateChatCompletionResponse as ChatCompletion,
    CreateChatCompletionStreamResponse as ChatCompletionChunk,
    CreateCompletionResponse as Completion,
)

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "openai"


class ChunkIterator:
    """Yields chunks"""

    def __init__(self, chunks: List[Completion]):
        self.chunks = chunks
        self.curr_chunk = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.curr_chunk >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self.curr_chunk]
        self.curr_chunk += 1
        return chunk


class DummyModel(OpenAIChatAdapterModel):
    data: Tuple[Completion, Completion]
    num_chunks: int

    def __init__(self, data: Tuple[Completion, Completion], num_chunks: int = 5):
        self.data = data
        self.num_chunks = num_chunks

    async def create_completion(
        self, request: CompletionRequest
    ) -> Union[Completion, AsyncIterator[Completion]]:
        params = request.params
        if params.stream:
            return ChunkIterator([self.data[1]] * self.num_chunks)
        else:
            return self.data[0]

    def apply_chat_template(
        self,
        messages: Iterable[ChatCompletionRequestMessage],
    ) -> ChatPrompt:
        return ChatPrompt(prompt="hello")


@pytest.fixture
def completion():
    with open(FIXTURES_PATH / "completion.json") as f:
        return Completion.model_validate_json(f.read())


@pytest.fixture
def completion_partial():
    with open(FIXTURES_PATH / "completion_partial.json") as f:
        return Completion.model_validate_json(f.read())


@pytest.fixture
def chat_completion():
    with open(FIXTURES_PATH / "chat_completion.json") as f:
        return ChatCompletion.model_validate_json(f.read())


@pytest.fixture
def chat_completion_chunk():
    with open(FIXTURES_PATH / "chat_completion_chunk.json") as f:
        return ChatCompletionChunk.model_validate_json(f.read())


@pytest.fixture
def completion_create_params():
    with open(FIXTURES_PATH / "completion_create_params.json") as f:
        return CreateCompletionRequest.model_validate_json(f.read())


@pytest.fixture
def chat_completion_create_params():
    with open(FIXTURES_PATH / "chat_completion_create_params.json") as f:
        return CreateChatCompletionRequest.model_validate_json(f.read())


@pytest.fixture
def dummy_model(completion: Completion, completion_partial: Completion):
    return DummyModel((completion, completion_partial))


class TestOpenAICreateCompletion:
    def test_completion_to_chat_completion(
        self, completion: Completion, chat_completion: ChatCompletion
    ):
        converted_chat_completion = (
            OpenAIChatAdapterModel.completion_to_chat_completion(
                completion, "assistant"
            )
        )
        assert (
            converted_chat_completion.model_dump_json()
            == chat_completion.model_dump_json()
        )

    @pytest.mark.asyncio
    async def test_create_completion_not_streaming(
        self,
        dummy_model: DummyModel,
        completion: Completion,
        completion_create_params: CreateCompletionRequest,
    ):
        request = CompletionRequest(params=completion_create_params)
        c = await dummy_model.create_completion(request)
        assert isinstance(c, Completion)
        assert c.model_dump_json(indent=2) == completion.model_dump_json(indent=2)

    @pytest.mark.asyncio
    async def test_create_completion_streaming(
        self,
        dummy_model: DummyModel,
        completion_partial: Completion,
        completion_create_params: CreateCompletionRequest,
    ):
        completion_create_params.stream = True
        request = CompletionRequest(params=completion_create_params)
        c = await dummy_model.create_completion(request)
        assert isinstance(c, AsyncIterator)
        num_chunks_consumed = 0
        async for chunk in c:
            assert chunk.model_dump_json(
                indent=2
            ) == completion_partial.model_dump_json(indent=2)
            num_chunks_consumed += 1
        assert num_chunks_consumed == dummy_model.num_chunks


class TestOpenAICreateChatCompletion:
    def test_completion_to_chat_completion(
        self, completion: Completion, chat_completion: ChatCompletion
    ):
        converted_chat_completion = (
            OpenAIChatAdapterModel.completion_to_chat_completion(
                completion, "assistant"
            )
        )
        assert (
            converted_chat_completion.model_dump_json()
            == chat_completion.model_dump_json()
        )

    @pytest.mark.asyncio
    async def test_create_chat_completion_not_streaming(
        self,
        dummy_model: DummyModel,
        chat_completion: ChatCompletion,
        chat_completion_create_params: CreateChatCompletionRequest,
    ):
        request = ChatCompletionRequest(params=chat_completion_create_params)
        c = await dummy_model.create_chat_completion(request)
        assert isinstance(c, ChatCompletion)
        assert c.model_dump_json(indent=2) == chat_completion.model_dump_json(indent=2)

    @pytest.mark.asyncio
    async def test_create_chat_completion_streaming(
        self,
        dummy_model: DummyModel,
        chat_completion_chunk: ChatCompletionChunk,
        chat_completion_create_params: CreateChatCompletionRequest,
    ):
        chat_completion_create_params.stream = True
        request = ChatCompletionRequest(params=chat_completion_create_params)
        c = await dummy_model.create_chat_completion(request)
        assert isinstance(c, AsyncIterator)
        num_chunks_consumed = 0
        async for chunk in c:
            assert chunk.model_dump_json(
                indent=2
            ) == chat_completion_chunk.model_dump_json(indent=2)
            num_chunks_consumed += 1
        assert num_chunks_consumed == dummy_model.num_chunks


class TestOpenAICompletionConversion:
    def test_completion_to_chat_completion(
        self, completion: Completion, chat_completion: ChatCompletion
    ):
        converted_chat_completion = (
            OpenAIChatAdapterModel.completion_to_chat_completion(
                completion, "assistant"
            )
        )
        assert (
            converted_chat_completion.model_dump_json()
            == chat_completion.model_dump_json()
        )

    def test_completion_to_chat_completion_chunk(
        self, completion_partial: Completion, chat_completion_chunk: ChatCompletionChunk
    ):
        converted_chat_completion_chunk = (
            OpenAIChatAdapterModel.completion_to_chat_completion_chunk(
                completion_partial, "assistant"
            )
        )
        assert converted_chat_completion_chunk.model_dump_json(
            indent=2
        ) == chat_completion_chunk.model_dump_json(indent=2)


class TestOpenAIParamsConversion:
    def test_convert_params(
        self,
        chat_completion_create_params: CreateChatCompletionRequest,
        completion_create_params: CreateCompletionRequest,
    ):
        converted_params = (
            OpenAIChatAdapterModel.chat_completion_params_to_completion_params(
                chat_completion_create_params,
                prompt=chat_completion_create_params.messages[0].content,
            )
        )
        assert converted_params == completion_create_params
