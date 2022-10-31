import email

from .context import save_message  # noqa: F401
from save_message.model import SaveRule


def create_message(
    to="terftwminal@yahoo.com",
    from_="Amazon Web Services <aws-verification@amazon.com>",
    date="Sat, 11 Jun 2022 13:45:43 +0000",
    subject="Your Request For Accessing AWS Resources Has Been Validated",
):
    return email.message_from_string(
        f"""Received: from 10.197.34.76
 by atlas321.free.mail.bf1.yahoo.com with HTTPS; Sat, 11 Jun 2022 13:45:44 +0000
Return-Path: <20220611134543d0fb989da85544d6869d86bb1bb0p0na@bounces.amazon.com>
X-Originating-Ip: [54.240.13.164]
Received-SPF: pass (domain of bounces.amazon.com designates 54.240.13.164 as permitted sender)
Received: from 54.240.13.164 (EHLO a13-164.smtp-out.amazonses.com)
 by 10.197.34.76 with SMTPs
 (version=TLS1_2 cipher=TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256);
 Sat, 11 Jun 2022 13:45:44 +0000
Date: {date}
From: {from_}
To: {to}
Message-ID: <0100018153037274-93360ac5-863e-41d9-b3dc-40613f5f025c-000000@email.amazonses.com>
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative; 
    boundary="----=_Part_6685915_1139391907.1654955143779"
Content-Length: 730

------=_Part_6685915_1139391907.1654955143779
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

Dear AWS Customer,

Thank you for using Amazon Web Services!

You recently requested an AWS Service that required additional validation. =
Your request has now been validated for AWS Europe (Paris) region(s). If yo=
u are still experiencing difficulty, please contact us at aws-verification@=
amazon.com <[[mailto:aws-verification@amazon.com]]>.

Thank you for your patience.

=E2=80=94The Amazon Web Services Team

This message was produced and distributed by Amazon Web Services, Inc. and =
affiliates, 410 Terry Ave. North, Seattle, WA 98109-5210.
------=_Part_6685915_1139391907.1654955143779--
"""
    )


def test_save_rule_matches_glob_subject():
    subject = "my subject"
    msg = create_message(subject=subject)
    rule = SaveRule(match_subject=f"{subject}*", save_to="/")

    assert rule.matches(msg)


def test_save_rule_matches_regex_subject():
    subject = "my subject"
    msg = create_message(subject=subject)
    rule = SaveRule(match_subject="/^my .+t$/", save_to="/")

    assert rule.matches(msg)


def test_save_rule_matches_glob_subject_fail():
    subject = "my subject"
    msg = create_message(subject=subject)
    rule = SaveRule(match_subject="my sub*z", save_to="/")

    assert not rule.matches(msg)


def test_save_rule_matches_regex_subject_fail():
    subject = "my subject"
    msg = create_message(subject=subject)
    rule = SaveRule(match_subject="/^my .+z$/", save_to="/")

    assert not rule.matches(msg)
