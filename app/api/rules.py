from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.database import get_cursor
from app.core.deps import get_current_user

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleContent(BaseModel):
    content: str
    title: str = ""


class RulesResponse(BaseModel):
    skin_quality: str = ""
    system_prompt: str = ""
    baseline: str = ""


RULE_TYPES = {"skin_quality", "system_prompt", "baseline"}


@router.get("", response_model=RulesResponse)
def get_rules(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    result: dict[str, str] = {}
    with get_cursor() as cur:
        cur.execute(
            "SELECT rule_type, content FROM user_rules WHERE user_id = %s",
            (user_id,),
        )
        for rule_type, content in cur.fetchall():
            result[rule_type] = content
    return RulesResponse(**result)


@router.put("/{rule_type}")
def save_rule(
    rule_type: str,
    body: RuleContent,
    current_user: dict = Depends(get_current_user),
):
    if rule_type not in RULE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"规则类型必须是: {', '.join(sorted(RULE_TYPES))}",
        )
    user_id = current_user["user_id"]
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO user_rules (user_id, rule_type, title, content)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE title = VALUES(title), content = VALUES(content)""",
            (user_id, rule_type, body.title, body.content),
        )
    return {"ok": True, "rule_type": rule_type, "title": body.title}
