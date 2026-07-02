"""
edges/routing.py — 条件边函数。

校验节点返回中性的判定令牌（passed / retry / abort），
由各图的 path_map 解释为具体目标节点。这样路由逻辑只描述
「校验结果」，不再耦合下游节点身份，避免语义陷阱。

重试次数语义（与 max_retries 含义一致）：
  retry_count 由 validate 节点在每次失败时 +1 累加；
  当 retry_count > max_retries 时放弃。
  因此一次原始调用 + max_retries 次重试 = 共 max_retries+1 次生成尝试。
"""
from backend.graph.state import AnimationState

# 中性令牌：只表达「校验判定结果」，不指代任何具体节点
TOKEN_PASSED = "passed"   # 校验通过，进入下一阶段
TOKEN_RETRY = "retry"     # 校验失败，可重试
TOKEN_ABORT = "abort"     # 校验失败且重试耗尽，终止


def _retry_left(state: AnimationState) -> bool:
    """是否还有重试机会。"""
    return state.get("retry_count", 0) <= state.get("max_retries", 2)


def after_validate_segments(state: AnimationState) -> str:
    """segments 校验后的判定。"""
    if state.get("segments_valid"):
        return TOKEN_PASSED
    return TOKEN_RETRY if _retry_left(state) else TOKEN_ABORT


def after_validate_narrative(state: AnimationState) -> str:
    """纯文案校验后的判定（三阶段拆分）。"""
    if state.get("narrative_valid"):
        return TOKEN_PASSED
    return TOKEN_RETRY if _retry_left(state) else TOKEN_ABORT


def after_validate_direction(state: AnimationState) -> str:
    """动画指导校验后的判定（三阶段拆分）。"""
    if state.get("direction_valid"):
        return TOKEN_PASSED
    return TOKEN_RETRY if _retry_left(state) else TOKEN_ABORT
