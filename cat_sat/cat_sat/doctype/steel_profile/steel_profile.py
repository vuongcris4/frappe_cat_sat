# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

import frappe
import re
from frappe.model.document import Document


class SteelProfile(Document):
	def before_save(self):
		# Normalize bundle_factors: split by any separator, remove empty, join with spaces
		if self.bundle_factors:
			# Split by comma, space, period, semicolon
			factors = [s.strip() for s in re.split(r'[,\s.;]+', self.bundle_factors) if s.strip()]
			# Filter to valid integers only
			valid_factors = []
			for f in factors:
				try:
					val = int(f)
					if val > 0 and val not in valid_factors:
						valid_factors.append(val)
				except ValueError:
					pass
			# Sort and join with spaces
			valid_factors.sort()
			self.bundle_factors = ' '.join(str(f) for f in valid_factors)
