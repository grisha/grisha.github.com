---
layout: post
title: "Simple Solution to Password Reuse"
date: 2013-05-31 17:12
comments: true
categories: 
---

<p>
Here's a <a href="http://en.wikipedia.org/wiki/KISS_principle">KISS</a> solution to all your password reuse
problems. It requires remembering only *one* strong password, lets you
have a virtually limitless number of passwords, and, most importantly,
does NOT store anything anywhere or transfer anything over the
network (100% browser-side Javascript).
</p>

<script type="text/javascript" src="/javascripts/sha.js"></script>
<script type="text/javascript" src="/javascripts/zxcvbn-async.js"></script>
<script type="text/javascript">
function calc_pw(n) {
  try {
    var pw_phrase = document.getElementById("pw_phrase");
    var keyword = document.getElementById("keyword"+n);
    var pw = document.getElementById("pw"+n);
    var strength = document.getElementById("strength");
    var hmacObj = new jsSHA(pw_phrase.value, "TEXT");
    pw.value = hmacObj.getHMAC(keyword.value, "TEXT", "SHA-512", "B64").substring(5,15);
    if (pw.value.search('!') === -1) pw.value = pw.value + '!'
    if (pw.value.search(/[0-9]/) === -1) pw.value = pw.value + '0'
  } catch(e) {
    pw.value = "ERROR: " + e;
  }
}
function pw_strength() {
    var pw_phrase = document.getElementById("pw_phrase");
    var score = zxcvbn(pw_phrase.value).score;
    if (score == '0') {strength.value = 'Very Weak'; strength.style.color = 'red'; }
    else if (score == '1') {strength.value = 'Weak'; strength.style.color = 'red'; }
    else if (score == '2') {strength.value = 'So so'; strength.style.color = 'orange'; }
    else if (score == '3') {strength.value = 'Okay'; strength.style.color = 'blue'; }
    else if (score == '4') {strength.value = 'Strong'; strength.style.color = 'green'; }
    else strength.value = '';
}
function check_pw2_same() {
  var pw_phrase = document.getElementById("pw_phrase");
  var pw_phrase2 = document.getElementById("pw_phrase2");
  var pw_same = document.getElementById("pw_same");
  if (pw_phrase.value === pw_phrase2.value)
    pw_same.value = 'Correct';
  else
    pw_same.value = 'Incorrect';
}
function clear_all() {
  document.getElementById("pw_phrase").value = '';
  document.getElementById("pw_phrase2").value = '';
  document.getElementById("strength").value = '';
  document.getElementById("pw_same").value = '';
  document.getElementById("keyword1").value = 'amazon';
  document.getElementById("keyword2").value = 'gmail';
  document.getElementById("keyword3").value = 'yahoo';
  document.getElementById("keyword4").value = 'foo';
  document.getElementById("keyword5").value = 'bar';
  document.getElementById("pw1").value = '';
  document.getElementById("pw2").value = '';
  document.getElementById("pw3").value = '';
  document.getElementById("pw4").value = '';
  document.getElementById("pw5").value = '';
}
</script>

<form action="#" method="get">
<fieldset style="margin: 3px 0px; border: 1px solid #000000; padding: 10px;">
<legend>Stupid Simple Password Generator</legend>
<h3>Step 1:</h3>
<p>
Think of a phrase you will always remember. Keep typing until the text
on the right says "strong". Punctuation, spaces, unusual words and
mixed case while not required, are generally a good idea. The most
important thing is that the script considers it <span style="color: green; font-weight: bold;">strong</span>.
</p>

<p> Make sure this passphrase is impossible to guess by people who
know you, e.g. don't pick quotes from your favorite song or
movie. Don't <em>ever</em> write it down or save it on your computer in any way or form!
<table border=0>
<tr><th>Passphrase: </th><td><input type="password" size="60" name="pw_phrase" id="pw_phrase" style="margin-right: 1em; margin-left: 1em;" onkeyup="pw_strength()" />
<th>Strength: </th><td><input tpye="text" size="10" name="strength" id="strength" style="font-weight: bold; margin-left: 1em;" readonly/></td></tr>
<tr><th>Verify: </th><td><input type="password" size="60" name="pw_phrase2" id="pw_phrase2" style="margin-right: 1em; margin-left: 1em;" onkeyup="check_pw2_same()" />
<th>Correct: </th><td><input tpye="text" size="10" name="pw_same" id="pw_same" style="font-weight: bold; margin-left: 1em;" readonly/></td></tr>
</table>
</p>

<h3>Step 2:</h3>
<p> Think of a short keyword describing a password, e.g. "amazon",
"gmail", etc. This word has to be easy to remember and there is no need for
it to be unique or hard to guess.</p>

<table border=0>
<tr><th>Keyword</th><th>Password</th></tr>
<tr><td><input type="text" size="30" name="keyword1" id="keyword1" value="gmail" onkeyup="calc_pw(1)" /></td><td><input type="text" size="30" name="pw1" id="pw1" style="margin-left: 1em;" readonly /></td></tr>
<tr><td><input type="text" size="30" name="keyword2" id="keyword2" value="gmail" onkeyup="calc_pw(2)" /></td><td><input type="text" size="30" name="pw2" id="pw2" style="margin-left: 1em;" readonly /></td></tr>
<tr><td><input type="text" size="30" name="keyword3" id="keyword3" value="gmail" onkeyup="calc_pw(3)" /></td><td><input type="text" size="30" name="pw3" id="pw3" style="margin-left: 1em;" readonly /></td></tr>
<tr><td><input type="text" size="30" name="keyword4" id="keyword4" value="gmail" onkeyup="calc_pw(4)" /></td><td><input type="text" size="30" name="pw4" id="pw4" style="margin-left: 1em;" readonly /></td></tr>
<tr><td><input type="text" size="30" name="keyword5" id="keyword5" value="gmail" onkeyup="calc_pw(5)" /></td><td><input type="text" size="30" name="pw5" id="pw5" style="margin-left: 1em;" readonly /></td></tr>
</table>
<br>
<p>That's it! You can regenerate any of the passwords above at any time by coming back to this page, all you need to know is the passphrase (and the keywords).</p>


</fieldset>
</form>
<span style="font-size: 12px">Fine print: This is a proof-of-concept, use at your own risk!</span>
<body onload="clear_all()"></body>


<h2>How does it work?</h2>

First, credits where they are due: This page uses <a href="https://github.com/Caligatio/">Brian Turek's</a>
excellent <a href="https://github.com/Caligatio/jsSHA">jsSHA</a> Javascript SHA lib and
<a href="https://github.com/lowe">Dan Wheeler's</a> amazing <a href="https://github.com/lowe/zxcvbn">zxcvbn</a>
password strength checking lib.

All we are doing here is computing a SHA-512 of the passphrase +
keyword, then selecting a substring of the result. (We also append a 0
and/or a ! to satisfy most password checker requirements for numbers
and punctuation).

If you don't trust that generated passwords are strong, just paste
them into the passphrase field, I assure you, no password here will
ever be weak. (Or, rather, it is <em>extremely</em> unlikely).

Some improvements could be made, but the point here is that there is
no reason to keep encrypted files with your passwords along with
software to open them around, all that's needed is <em>one</em> strong
password and a well established and easily available algorithm.


