from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    name: str
    args: Dict[str, Any] = Field(..., alias="args")


class ToolCall(BaseModel):
    function: FunctionCall


class ToolResponse(BaseModel):
    name: str
    content: str


class Part(BaseModel):
    text: Optional[str] = None
    inline_data: Optional[dict] = Field(None, alias="inlineData")
    function_call: Optional[FunctionCall] = Field(None, alias="functionCall")
    tool_calls: Optional[List[ToolCall]] = Field(None, alias="toolCalls")
    tool_response: Optional[ToolResponse] = Field(None, alias="toolResponse")


class Content(BaseModel):
    role: Optional[str] = None
    parts: List[Part]


class GenerationConfig(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = Field(None, alias="topP")
    top_k: Optional[int] = Field(None, alias="topK")
    candidate_count: Optional[int] = Field(None, alias="candidateCount")
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    stop_sequences: Optional[List[str]] = Field(None, alias="stopSequences")


class SafetySetting(BaseModel):
    category: str
    threshold: Literal[
        "HARM_BLOCK_UNSPECIFIED",
        "BLOCK_LOW_AND_ABOVE",
        "BLOCK_MEDIUM_AND_ABOVE",
        "BLOCK_NONE",
    ]


class Tool(BaseModel):
    function_declarations: List[dict] = Field(..., alias="functionDeclarations")


class ToolConfig(BaseModel):
    function_calling_config: Optional[Dict[str, Any]] = Field(
        None, alias="functionCallingConfig"
    )


class Request(BaseModel):
    contents: List[Content]
    systemInstruction: Content
    generation_config: Optional[GenerationConfig] = Field(
        None, alias="generationConfig"
    )
    safety_settings: Optional[List[SafetySetting]] = Field(None, alias="safetySettings")
    tools: Optional[List[Tool]] = None
    tool_config: Optional[ToolConfig] = Field(None, alias="toolConfig")


class Candidate(BaseModel):
    content: Content
    finish_reason: Optional[str] = Field(None, alias="finishReason")
    safety_ratings: Optional[List[dict]] = Field(None, alias="safetyRatings")
    citation_metadata: Optional[dict] = Field(None, alias="citationMetadata")


class PromptFeedback(BaseModel):
    block_reason: Optional[str] = Field(None, alias="blockReason")
    safety_ratings: Optional[List[dict]] = Field(None, alias="safetyRatings")


class Response(BaseModel):
    candidates: Optional[List[Candidate]] = None
    prompt_feedback: Optional[PromptFeedback] = Field(None, alias="promptFeedback")
