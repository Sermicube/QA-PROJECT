from pydantic import BaseModel


class TermIn(BaseModel):
    name: str
    definition: str
    synonyms: list[str] = []


class TermOut(BaseModel):
    name: str
    definition: str
    synonyms: list[str]


class KnowledgeQueryIn(BaseModel):
    text: str
    module_filter: str | None = None


class KnowledgeQueryOut(BaseModel):
    results: list[dict]


class RegressionSuggestion(BaseModel):
    cert_id: str
    cert_title: str
    tc_id: str
    tc_name: str
    tc_result: str
