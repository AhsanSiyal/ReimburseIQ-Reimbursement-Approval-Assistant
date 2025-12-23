SYSTEM_POLICY_ANALYST = """You are a reimbursement policy analyst.
You MUST ONLY use the provided POLICY EXCERPTS to justify decisions.
If a needed rule is not present in the excerpts, state that clearly.

You MUST return ONLY valid JSON with EXACTLY these top-level keys:
- decision: one of ["APPROVE_RECOMMENDED","REJECT_RECOMMENDED","NEEDS_MORE_INFO"]
- summary: string
- lines: array of { line_id, status, issues, suggested_fix }
- missing_info: array of strings
- citations: array of { rule_id, snippet, section_title?, source_path? }

No markdown. No extra commentary. No additional keys.
"""

def build_user_prompt(claim: dict, deterministic_results: dict, policy_excerpts: list) -> str:
    excerpts_txt = []
    for i, ex in enumerate(policy_excerpts, start=1):
        excerpts_txt.append(
            f"[EXCERPT {i}]\n"
            f"Section: {ex.get('section_title')}\n"
            f"Rule IDs: {', '.join(ex.get('rule_ids') or [])}\n"
            f"Text:\n{ex.get('text')}\n"
        )

    return (
        "Evaluate the reimbursement claim against the policy excerpts.\n\n"
        "CLAIM (JSON):\n"
        f"{claim}\n\n"
        "DETERMINISTIC CHECK RESULTS (JSON):\n"
        f"{deterministic_results}\n\n"
        "POLICY EXCERPTS:\n"
        + "\n".join(excerpts_txt)
    )
