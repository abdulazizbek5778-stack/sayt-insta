from django.contrib.auth.password_validation import (
	CommonPasswordValidator,
	MinimumLengthValidator,
	NumericPasswordValidator,
	UserAttributeSimilarityValidator,
)


class UzbekUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
	def get_error_message(self):
		return 'Parol %(verbose_name)s ma’lumotlariga juda o‘xshash.'


class UzbekMinimumLengthValidator(MinimumLengthValidator):
	def get_error_message(self):
		return 'Parol kamida %(min_length)d ta belgidan iborat bo‘lishi kerak.'


class UzbekCommonPasswordValidator(CommonPasswordValidator):
	def get_error_message(self):
		return 'Bu parol juda ommabop. Boshqa parol tanlang.'


class UzbekNumericPasswordValidator(NumericPasswordValidator):
	def get_error_message(self):
		return 'Parol faqat raqamlardan iborat bo‘lishi mumkin emas.'