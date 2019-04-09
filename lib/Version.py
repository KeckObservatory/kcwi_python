
__all__ = ('version')

# Component files in the module will append their CVS/SVN $Revision string to
# the versions list. The version() function builds a 'total' version number
# that is the sum of all contributed values.

versions = []

append = versions.append
append ('$Revision: 87786 $')


def version ():
	''' Return a version number for this module. The version
	    number is computed by multiplying the major CVS revision of
	    each individual component by 1,000, directly adding the minor
	    version, and summing the results. SVN revision numbers are
	    strictly added.
	'''

	value = version.value

	if value == None:
		value = buildVersion ()
		version.value = value

	return value


version.value = None



def buildVersion ():

	sample = versions[0]
	revision = sample.split ()[1]

	try:
		int (revision)
	except (ValueError, TypeError):
		return buildFloatVersion ()
	else:
		return buildIntVersion ()



def buildFloatVersion ():

	total = 0

	for subversion in versions:
		number = subversion.split ()[1]

		left,right = number.split ('.')
		total += int (left) * 1000
		total += int (right)

	return total



def buildIntVersion ():

	total = 0

	for subversion in versions:
		number = subversion.split ()[1]
		total += int (number)

	return total
