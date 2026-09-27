"""Curated fictional policy questions. Two independent forms, same four skills."""


def add_banks(course):
    diagnostic = [
        (
            "What evidence is required for an expense claim?",
            ["An itemized receipt", "Only a bank statement", "A verbal description"],
            0,
        ),
        (
            "What is the normal expense submission window?",
            [
                "30 calendar days after purchase",
                "30 business days after purchase",
                "Any time in the same financial year",
            ],
            0,
        ),
        (
            "When must a purchase above SGD 200 receive written manager approval?",
            [
                "After Finance reimburses it",
                "Before the purchase",
                "Only if the receipt is missing",
            ],
            1,
        ),
        (
            "How long does Finance take to review a complete claim?",
            ["Five calendar days", "Five business days", "Thirty calendar days"],
            1,
        ),
    ]
    final = [
        (
            "Maya lost the itemized receipt but has a bank statement. What should she do before submitting?",
            [
                "Submit the statement alone",
                "Request a duplicate receipt from the supplier",
                "Submit a second claim to explain the missing receipt",
            ],
            1,
        ),
        (
            "An employee submits a claim 35 calendar days after purchase. How should it be handled?",
            [
                "Accept it automatically because it is under 30 business days",
                "Reject it permanently without review",
                "Refer it for manager review; acceptance is not automatic",
            ],
            2,
        ),
        (
            "You plan to buy equipment costing SGD 250 tomorrow. What should you do today?",
            [
                "Obtain written manager approval and later attach it to the claim",
                "Buy first and request approval with the receipt",
                "Split the claim into two entries to avoid approval",
            ],
            0,
        ),
        (
            "Finance returns your incomplete claim asking for information. What is the appropriate next step?",
            [
                "Correct the returned claim with the missing information",
                "Submit the same expense again as a new claim",
                "Assume payment will arrive after five calendar days",
            ],
            0,
        ),
    ]

    def form(rows):
        return [
            dict(
                prompt=p,
                options=o,
                answer=a,
                explanation=course["lessons"][i]["text"],
                skill=i,
            )
            for i, (p, o, a) in enumerate(rows)
        ]

    course["questions"] = form(diagnostic)
    course["assessment_questions"] = form(final)
    course["origin"] = (
        "Curated fictional demo • independent diagnostic and scenario assessment"
    )
    return course
