# Participant protocol requirements

The default environment accepts sandbox studies only. Configure `ETHICS_PROTOCOL_ID`, `ETHICS_CONSENT_TEXT` and `RESEARCH_REGISTRATION_CODE` only after institutional ethics review and the required privacy and legal review. Use the approved consent text, including responsible institution, contact, eligibility, risks, use of data, retention, withdrawal deadline, any compensation and intended sharing. The service returns a text fingerprint as the consent version and rejects stale versions. Archive the approved text alongside the protocol separately.

The sandbox consent screen demonstrates adult eligibility and consent. It records no name or contact details, keeps a hashed withdrawal credential on the server, and enables a participant to withdraw with the key held in their browser. A real deployment needs a recovery mechanism for lost credentials approved by the institution. Review every downstream export, backup and derivative before promising deletion timing.

Never treat no-purchase or other hypothetical selections as purchase transactions. Record genuine incentive conditions and choice opportunities separately. Publish aggregate results with minimum cell sizes specified by the approved protocol.
