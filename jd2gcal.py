# The function in this library was copied and modified from the excellent JDCal library by Prasanth Nair.
# The original copyright notice and licence follows.
"""
Copyright (c) 2011, Prasanth Nair
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import datetime
from math import modf

def jd2gcal(jd=None, ms=None, tz=None):
	if jd is None:
		return None
	if ms is None:
		ms = 0
	f, jd_i = modf(jd)
	# Set JD to noon of the current date. Fractional part is the
	# fraction from midnight of the current date.
	if -0.5 < f < 0.5:
		f += 0.5
	elif f >= 0.5:
		jd_i += 1
		f -= 0.5
	elif f <= -0.5:
		jd_i -= 1
		f += 1.5
	l = jd_i + 68569
	n = modf((4 * l) / 146097.0)[1]
	l -= modf(((146097 * n) + 3) / 4.0)[1]
	i = modf((4000 * (l + 1)) / 1461001)[1]
	l -= modf((1461 * i) / 4.0)[1] - 31
	j = modf((80 * l) / 2447.0)[1]
	day = l - modf((2447 * j) / 80.0)[1]
	l = modf(j / 11.0)[1]
	month = j + 2 - (12 * l)
	year = 100 * (n - 49) + i + l
	return datetime.datetime(int(year) if year >= 1 else 1, int(month) if month >= 1 else 1, int(day) if day >= 1 else 1) + datetime.timedelta(milliseconds=ms)
