package main

import (
	"os"
	"testing"
)

func TestChatUserPart(t *testing.T) {
	cases := map[string]string{
		"491732532061@s.whatsapp.net":    "491732532061",
		"491732532061:12@s.whatsapp.net": "491732532061",
		"491732532061":                   "491732532061",
		"123-456@g.us":                   "123-456",
	}
	for in, want := range cases {
		if got := chatUserPart(in); got != want {
			t.Errorf("chatUserPart(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestIsAllowedChat(t *testing.T) {
	os.Unsetenv("WHATSAPP_ALLOWED_JIDS")
	loadAllowedChatJIDs()
	if !isAllowedChat("000@s.whatsapp.net") {
		t.Error("expected allow-all when WHATSAPP_ALLOWED_JIDS unset")
	}

	os.Setenv("WHATSAPP_ALLOWED_JIDS", "491732532061@s.whatsapp.net")
	loadAllowedChatJIDs()
	if !isAllowedChat("491732532061@s.whatsapp.net") {
		t.Error("expected Zohair allowed")
	}
	if !isAllowedChat("491732532061:3@s.whatsapp.net") {
		t.Error("expected Zohair allowed with device suffix")
	}
	if isAllowedChat("999999@s.whatsapp.net") {
		t.Error("expected non-allowlisted chat blocked")
	}
}
