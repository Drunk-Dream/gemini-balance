from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    id: Optional[str] = None
    name: str
    args: Dict[str, Any] = Field(..., alias="args")


class FunctionResponse(BaseModel):
    id: Optional[str] = None
    name: str
    response: Dict[str, Any] = Field(..., alias="response")
    willContinue: Optional[bool] = Field(None, alias="willContinue")


class FileData(BaseModel):
    language: str
    code: str


class Part(BaseModel):
    thought: Optional[bool] = None
    thought_signature: Optional[str] = Field(None, alias="thoughtSignature")
    text: Optional[str] = None
    inline_data: Optional[dict] = Field(None, alias="inlineData")
    function_call: Optional[FunctionCall] = Field(None, alias="functionCall")
    function_response: Optional[FunctionResponse] = Field(
        None, alias="functionResponse"
    )
    file_data: Optional[FileData] = Field(None, alias="fileData")


class Content(BaseModel):
    role: Optional[str] = None
    parts: List[Part]


class ThinkingConfig(BaseModel):
    include_thoughts: Optional[bool] = Field(None, alias="includeThoughts")
    thinking_budget: Optional[int] = Field(None, alias="thinkingBudget")


class GenerationConfig(BaseModel):
    response_mime_type: Optional[str] = Field(None, alias="responseMimeType")
    temperature: Optional[float] = None
    top_p: Optional[float] = Field(None, alias="topP")
    top_k: Optional[int] = Field(None, alias="topK")
    seed: Optional[int] = None
    candidate_count: Optional[int] = Field(None, alias="candidateCount")
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    stop_sequences: Optional[List[str]] = Field(None, alias="stopSequences")
    presence_penalty: Optional[float] = Field(None, alias="presencePenalty")
    frequency_penalty: Optional[float] = Field(None, alias="frequencyPenalty")
    response_logprobs: Optional[bool] = Field(None, alias="responseLogprobs")
    logprobs: Optional[int] = None
    enable_enhanced_civic_answers: Optional[bool] = Field(
        None, alias="enableEnhancedCivicAnswers"
    )
    thinking_config: Optional[ThinkingConfig] = Field(None, alias="thinkingConfig")


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
    # systemInstruction: Content
    system_instruction: Optional[Content] = Field(None, alias="systemInstruction")
    generation_config: Optional[GenerationConfig] = Field(
        None, alias="generationConfig"
    )
    safety_settings: Optional[List[SafetySetting]] = Field(None, alias="safetySettings")
    cached_content: Optional[str] = Field(None, alias="cachedContent")
    tools: Optional[List[Tool]] = None
    tool_config: Optional[ToolConfig] = Field(None, alias="toolConfig")


class Candidate(BaseModel):
    content: Content
    finish_reason: Optional[str] = Field(None, alias="finishReason")
    safety_ratings: Optional[List[dict]] = Field(None, alias="safetyRatings")
    citation_metadata: Optional[dict] = Field(None, alias="citationMetadata")
    token_count: Optional[int] = Field(None, alias="tokenCount")
    avgLogprobs: Optional[float] = Field(None, alias="avgLogprobs")
    index: Optional[int] = None


class PromptFeedback(BaseModel):
    block_reason: Optional[str] = Field(None, alias="blockReason")
    safety_ratings: Optional[List[dict]] = Field(None, alias="safetyRatings")


class UsageMetadata(BaseModel):
    prompt_token_count: Optional[int] = Field(None, alias="promptTokenCount")
    cached_content_token_count: Optional[int] = Field(
        None, alias="cachedContentTokenCount"
    )
    candidates_token_count: Optional[int] = Field(None, alias="candidatesTokenCount")
    tool_use_prompt_token_count: Optional[int] = Field(
        None, alias="toolUsePromptTokenCount"
    )
    thoughts_token_count: Optional[int] = Field(None, alias="thoughtsTokenCount")
    total_token_count: Optional[int] = Field(None, alias="totalTokenCount")


class Response(BaseModel):
    candidates: Optional[List[Candidate]] = None
    prompt_feedback: Optional[PromptFeedback] = Field(None, alias="promptFeedback")
    usage_metadata: Optional[UsageMetadata] = Field(None, alias="usageMetadata")
    model_version: Optional[str] = Field(None, alias="modelVersion")
    response_id: Optional[str] = Field(None, alias="responseId")
