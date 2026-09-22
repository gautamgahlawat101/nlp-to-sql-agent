"""
tests/test_queries.py

Benchmark suite: runs a fixed set of test questions through the full agent
pipeline and reports a pass rate — this is what turns "the agent seems to
work" into an actual, measurable number.

A test passes if:
  - for a normal question: the agent returns status "success" AND every
    table listed in expected_tables appears somewhere in the generated SQL
  - for a deliberately ambiguous question (expect_clarify=True): the agent
    returns status "clarify" instead of guessing

Usage:
    python tests/test_queries.py
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.conversation_manager import ask

TEST_CASES = [
    {"question": "How many customers do we have?", "expected_tables": ["customer.customers"]},
    {"question": "List all campaign channels", "expected_tables": ["campaign.campaign_channels"]},
    {"question": "What is the total revenue from all transactions?", "expected_tables": ["sales.transactions"]},
    {"question": "Top 5 customers by revenue", "expected_tables": ["customer.customers", "sales.orders", "sales.transactions"]},
    {"question": "Which campaigns generated the most orders?", "expected_tables": ["campaign.campaigns", "sales.orders"]},
    {"question": "What products are in the Electronics category?", "expected_tables": ["products.products", "products.product_categories"]},
    {"question": "How many orders were cancelled?", "expected_tables": ["sales.orders"]},
    {"question": "What is the average order value by payment method?", "expected_tables": ["sales.transactions"]},
    {"question": "Which customers are in the High Value segment?", "expected_tables": ["customer.customers", "customer.customer_segments", "customer.customer_segment_map"]},
    {"question": "What is the current stock level for each product?", "expected_tables": ["products.inventory", "products.products"]},
    {"question": "Show loyalty point balances for Gold tier members", "expected_tables": ["loyalty.loyalty_accounts"]},
    {"question": "What rewards can be redeemed for under 1000 points?", "expected_tables": ["loyalty.loyalty_rewards"]},
    {"question": "Did the stock price increase in the days after our campaigns launched?", "expected_tables": ["market_data.daily_prices", "campaign.campaigns"]},
    {"question": "What was our closing stock price trend over the last quarter?", "expected_tables": ["market_data.daily_prices"]},
    {"question": "Did we outperform the NIFTY 50 index last month?", "expected_tables": ["market_data.daily_prices", "market_data.market_indices"]},
    {"question": "Which warehouse has the most inventory?", "expected_tables": ["products.inventory"]},
    {"question": "How many campaigns are currently active?", "expected_tables": ["campaign.campaigns"]},
    {"question": "What's the total spend on Instagram Ads campaigns?", "expected_tables": ["campaign.campaigns", "campaign.campaign_channels"]},
    {"question": "Show me customers who signed up in the last 30 days", "expected_tables": ["customer.customers"]},
    {"question": "Which product categories have the highest average unit price?", "expected_tables": ["products.products", "products.product_categories"]},
    {"question": "List loyalty transactions where points were redeemed", "expected_tables": ["loyalty.loyalty_transactions"]},
    {"question": "What's the click-through rate for each campaign?", "expected_tables": ["campaign.campaign_performance"]},
    {"question": "top customers", "expect_clarify": True},
    {"question": "show me the best campaigns", "expect_clarify": True},
    {"question": "what's popular", "expect_clarify": True},
]


def run_benchmark():
    passed = 0
    failed = []

    for i, case in enumerate(TEST_CASES, 1):
        question = case["question"]
        expect_clarify = case.get("expect_clarify", False)
        print(f"[{i}/{len(TEST_CASES)}] {question}")

        result = ask(question)

        try:
            result = ask(question)
        except Exception as e:
            result = {"status": "error", "message": f"API/network error: {e}"}

        if expect_clarify:
            ok = result["status"] == "clarify"
            detail = result.get("question", result.get("message", ""))
        else:
            if result["status"] != "success":
                ok = False
                detail = result.get("message", result.get("question", "no SQL generated"))
            else:
                sql_lower = result["sql"].lower()
                missing = [t for t in case["expected_tables"] if t.lower() not in sql_lower]
                ok = len(missing) == 0
                detail = result["sql"] if ok else f"missing tables: {missing} | got: {result['sql']}"

        if ok:
            passed += 1
            print("   PASS")
        else:
            failed.append({"question": question, "detail": detail})
            print(f"   FAIL — {detail}")

    total = len(TEST_CASES)
    pct = (passed / total) * 100
    print(f"\n{'=' * 50}")
    print(f"RESULT: {passed}/{total} passed ({pct:.1f}%)")
    print(f"{'=' * 50}")

    if failed:
        print("\nFailures:")
        for f in failed:
            print(f"  - {f['question']}")
            print(f"    {f['detail']}\n")


if __name__ == "__main__":
    run_benchmark()