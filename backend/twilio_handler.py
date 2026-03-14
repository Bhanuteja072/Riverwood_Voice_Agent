from twilio.twiml.voice_response import Gather, VoiceResponse

# Twilio voice for fallback if not using ElevenLabs
TWILIO_VOICE = "Polly.Aditi"  # Indian English AWS Polly voice via Twilio


def make_gather_response(
    speech_text: str,
    action_url: str,
    voice_url: str | None = None
) -> str:
    """
    Build TwiML that:
    1. Plays the agent's audio (or speaks text)
    2. Listens for customer response
    Returns TwiML XML string.
    """
    response = VoiceResponse()

    gather = Gather(
        input="speech",           # listen for speech
        action=action_url,        # where to send customer's speech
        method="POST",
        speech_timeout="3",       # wait 1 second after customer stops speaking
        language="en-IN"          # Indian English only
    )

    if voice_url:
        # Play pre-generated ElevenLabs audio
        gather.play(voice_url)
    else:
        # Fallback: Twilio reads the text directly
        gather.say(speech_text, voice=TWILIO_VOICE, language="en-IN")

    response.append(gather)

    # If customer doesn't speak, re-prompt once
    response.say(
        "Can you hear me clearly?",
        voice=TWILIO_VOICE,
        language="en-IN"
    )

    return str(response)


def make_voicemail_response(customer_name: str) -> str:
    """TwiML for when call goes to voicemail."""
    response = VoiceResponse()
    response.say(
        f"Hello, {customer_name}. This is Riya from Riverwood Projects LLP. "
        "I have an important update for you. "
        "Please call us back at 8572070707. "
        "Thank you.",
        voice=TWILIO_VOICE,
        language="en-IN"
    )
    response.hangup()
    return str(response)


def make_end_call_response() -> str:
    """TwiML to gracefully end the call."""
    response = VoiceResponse()
    response.say(
        "Thank you very much. Have a wonderful day!",
        voice=TWILIO_VOICE,
        language="en-IN"
    )
    response.hangup()
    return str(response)