import pytest
from services.factual_consistency import find_factual_inconsistency


@pytest.fixture
def consistent_texts():
    return {
        "original": "Patient John Doe, 45, presented with chest pain and shortness of breath.",
        "summary": "Patient John Doe, 45, presented with chest pain and shortness of breath."
    }

@pytest.fixture
def inconsistent_texts():
    return {
        "original": "Patient reported headache and nausea today.",
        "summary": "Patient complained of chest pain and dizziness yesterday."
    }

@pytest.fixture
def partial_match_texts():
    return {
        "original": "Patient has diabetes and takes blood pressure medication.",
        "summary": "Patient has diabetes and high blood pressure."
    }

def test_verify_factual_consistency_consistent(consistent_texts):
    """Test verification with fully consistent text
    
    :param consistent_texts: Fixture with matching original and summary texts
    :type consistent_texts: dict
    """
    issues = find_factual_inconsistency(
        consistent_texts["original"], 
        consistent_texts["summary"]
    )

    assert issues == []

def test_verify_factual_consistency_inconsistent(inconsistent_texts):
    """Test verification with inconsistent entities
    
    :param inconsistent_texts: Fixture with mismatched original and summary texts
    :type inconsistent_texts: dict
    """
    issues = find_factual_inconsistency(
        inconsistent_texts["original"], 
        inconsistent_texts["summary"]
    )
    
    assert len(issues) > 0

def test_verify_factual_consistency_partial_match(partial_match_texts):
    """Test verification with partial entity matches
    
    :param partial_match_texts: Fixture with partially matching original and summary texts
    :type partial_match_texts: dict
    """
    issues = find_factual_inconsistency(
        partial_match_texts["original"], 
        partial_match_texts["summary"]
    )
    
    assert issues == ['high blood pressure']

@pytest.mark.parametrize("original,summary,expected", [
    ("Some text", "", (True, [], 1.0)),  # Empty summary
    ("", "Some summary", (False, [], 0.0)),  # Empty original
    ("", "", (True, [], 1.0)),  # Both original and summary empty
])
def test_verify_factual_consistency_empty_inputs(original, summary, expected):
    """Test verification with empty inputs
    
    :param original: Original text input
    :type original: str
    :param summary: Summary text input
    :type summary: str
    :param expected: Expected result tuple
    :type expected: tuple
    """
    issues = find_factual_inconsistency(original, summary)
    assert issues == expected[1]  # Just check the issues part

def test_verify_factual_consistency_case_insensitivity():
    """Test that verification is case insensitive
    
    Verifies that the factual consistency check ignores case differences
    between the original text and summary.
    """
    original = "Patient has Diabetes and High Blood Pressure."
    summary = "patient has diabetes and high blood pressure"
    
    issues = find_factual_inconsistency(original, summary)
    
    assert issues == []


def test_verify_factual_consistency_with_full_transcript():
    """Test verification when summary adds context not in original
    
    Verifies that the factual consistency check correctly identifies
    entities in the summary that were not present in the original text.
    """
    original = """ Hi, Mr. Jones.  How are you?  I'm good, Dr. Smith.  Thanks to see you.  Thanks to see you again.  What brings you back?  Well, my back's been hurting again.  I see.  I've seen you a number of times for this, haven't I?  Yeah, well, ever since I got hurt on the job three years ago.  It's something that just keeps coming back.  You know, it'll be fine for a while.  And then I'll end down or I'll move in a weird way.  And then boom, it'll just go out again.  Unfortunately, that can happen.  And I do have quite a few patients who get reoccurring episodes of back pain.  Have you been keeping up with the therapy that we had you on before?  Which the pills?  Actually, I was talking about the physical therapy that we had you doing.  The pills are only meant for short term because they don't actually prevent the back pain from coming back.  See, yeah, I've once my back started feeling better.  I was happy not to go to the therapist anymore.  Why was that?  Well, it started to become kind of a hassle with my work schedule and the cost was an issue.  But I was able to get back to work.  And I could use the money.  Do you think the physical therapy was helping?  Yeah, what was slow going at first?  I see.  Physical therapy is a bit slower than medications.  But the point is to build up the core muscles in your back and your abdomen.  Physical therapy is also less invasive than medications.  So that's why we had you doing the therapy.  But you mentioned that cost was getting to be a real issue for you.  Can you tell me more about that?  Well, the insurance I had only covered a certain number of sessions.  And then they moved my therapy office because they were trying to work out my schedule at work.  But that was really far away.  And then I had to deal with parking and it just started to get really expensive.  Got it.  I understand.  So for now, I'd like you to try using a heating pad for your back pain.  So that should help in the short term.  Our goal is to get your back pain under better control without creating additional problems for you like cost.  Let's talk about some different options and the pros and cons of each.  So the physical therapy is actually really good for your back pain.  But there are other things we can be doing to help.  Yes, I definitely don't need to lose any more time at work and just lie around the house all day.  Okay, whether some alternative therapies like yoga or tai chi classes or meditation therapies that might be able to help.  And they might also be closer to you and be less expensive.  Would that be something you'd be interested in?  Sure, that'd be great.  Good.  Let's talk about some of the other costs of your care.  In the past we had you on some tram at all because the physical therapy alone wasn't working.  Yeah, that medicine was working really well.  But again, the cost to take out really expensive.  Yeah, yeah.  So that is something in the future we could order something like a generic medication.  And then there are also resources for people to look up the cheapest cost of their medications.  But for now, I'd like to stick with the non prescription medications.  And if we can have you go to yoga or tai chi classes like I mentioned, that could alleviate the need for ordering prescriptions.  Okay, yeah, that sounds good.  Okay, great, great.  Are there any other costs that are a problem for you and your care?  Well, my insurance isn't going down, but that seems to be the case for everybody that I talk to, but I should be able to make it work.  Yeah.  And fortunately, that is an issue for a lot of people.  But I would encourage you during open season to look at your different insurance options,  to see which plan is more cost-effective for you.  Okay, yeah, that sounds great.  Great.  Well, I appreciate you talking to me today.  Yeah, I'm glad you're able to come in.  What I'll do is I'll have my office team research, the different things that you and I talked about today.  And then let's set a time early next week, say Tuesday, where we can talk over the phone,  about what we were able to come up with for you and see if those would work for you.  Okay, great.  Great. """
    summary = """## SOAP Note

**Subjective:** 
Mr. Jones reports his back pain has been recurring since an injury at work three years ago. He describes it as coming and going, with periods of improvement followed by episodes where he experiences discomfort and limited mobility.  He notes that the pain is exacerbated by movement and can be debilitating. He previously had physical therapy but stopped due to cost concerns related to his insurance coverage and the distance of his therapy office. He also mentions a preference for non-prescription medications, which were effective in the past, but are expensive. 

**Objective:**
None.

**Assessment:**  
Mr. Jones presents with chronic back pain likely stemming from an occupational injury. His history suggests a pattern of recurring episodes, potentially related to muscle weakness and instability. He reports difficulty managing the cost of his care, including physical therapy and medications. 

**Plan:**
1. **Short-term Management:** Recommend using a heating pad for pain relief.
2. **Alternative Therapies:** Explore options like yoga, tai chi, or meditation classes as potential alternatives to prescription medication and potentially more affordable.
3. **Insurance Review:** Encourage Mr. Jones to review his insurance plan during open enrollment to identify cost-effective options. 
4. **Follow-up:** Schedule a phone call with Mr. Jones next week to discuss the proposed management strategies, including alternative therapies and potential cost-saving measures.  


"""
    
    issues = find_factual_inconsistency(original, summary)
    assert len(issues) > 0

def test_verify_factual_consistency_with_medical_entities():
    """Test verification with medical entities and medications
    
    Verifies that the factual consistency check correctly identifies medical entities
    and medications that were not present in the original conversation.
    """
    # Example conversation text from fact_testdrive.py
    original = """
    Dr. Smith met with John Doe on March 5, 2025. John mentioned back pain and hypertension.
    Dr. Smith prescribed lisinopril and scheduled a blood test for next week.
    """
    
    # Example summary text with hallucinations (from fact_testdrive.py)
    summary = """
    Dr. Smith met John Doe on March 5, 2025, to discuss back pain and cancer.
    He prescribed lisinopril and metformin.
    """
    
    issues = find_factual_inconsistency(original, summary)
    
    # The summary contains "cancer" and "metformin" which aren't in the original
    assert len(issues) > 0
    
    # Check for specific hallucinated entities
    # Note: The exact entities detected may vary based on the NER model used
    # but at minimum, we expect to find some inconsistencies
    assert any(entity in ['cancer', 'metformin'] for entity in issues)
