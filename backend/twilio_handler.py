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
        speech_timeout="4",       # wait 3 seconds after customer stops speaking
        language="hi-IN en-IN"    # Hindi and Indian English
    )

    if voice_url:
        # Play pre-generated ElevenLabs audio
        gather.play(voice_url)
    else:
        # Fallback: Twilio reads the text directly
        gather.say(speech_text, voice=TWILIO_VOICE, language="hi-IN")

    response.append(gather)

    # If customer doesn't speak, re-prompt once
    response.say(
        "Kya aap mujhe sun pa rahe hain?",
        voice=TWILIO_VOICE,
        language="hi-IN"
    )

    return str(response)


def make_voicemail_response(customer_name: str) -> str:
    """TwiML for when call goes to voicemail."""
    response = VoiceResponse()
    response.say(
        f"Namaste, {customer_name} ji. "
        "Main Riya bol rahi hoon Riverwood Projects LLP se. "
        "Aapke liye ek important update hai. "
        "Please humein 8572070707 par callback karein. "
        "Dhanyawaad.",
        voice=TWILIO_VOICE,
        language="hi-IN"
    )
    response.hangup()
    return str(response)


def make_end_call_response() -> str:
    """TwiML to gracefully end the call."""
    response = VoiceResponse()
    response.say(
        "Bahut bahut dhanyawaad. Aapka din shubh ho!",
        voice=TWILIO_VOICE,
        language="hi-IN"
    )
    response.hangup()
    return str(response)