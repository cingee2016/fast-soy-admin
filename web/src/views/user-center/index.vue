<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { fetchUpdatePassword, fetchUpdateProfile } from '@/service/api';
import { userGenderOptions } from '@/constants/business';
import { useAuthStore } from '@/store/modules/auth';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { translateOptions } from '@/utils/common';
import { $t } from '@/locales';

const authStore = useAuthStore();
const {
  formRef: profileFormRef,
  validate: validateProfile,
  restoreValidation: restoreProfileValidation
} = useNaiveForm();
const {
  formRef: passwordFormRef,
  validate: validatePassword,
  restoreValidation: restorePasswordValidation
} = useNaiveForm();
const { formRules, patternRules, createConfirmPwdRule, createRequiredRule } = useFormRules();

const profileModel = reactive<Api.Auth.UpdateProfileParams>({
  nickName: '',
  userGender: '3',
  userEmail: null,
  userPhone: null
});

const passwordModel = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const profileSubmitting = ref(false);
const passwordSubmitting = ref(false);

const profileRules = computed(() => ({
  nickName: createRequiredRule($t('form.required')),
  userEmail: patternRules.email,
  userPhone: patternRules.phone
}));

const passwordRules = computed(() => ({
  oldPassword: createRequiredRule($t('page.userCenter.password.oldPasswordPlaceholder')),
  newPassword: formRules.pwd,
  confirmPassword: createConfirmPwdRule(passwordModel.newPassword)
}));

function syncProfileModel() {
  profileModel.nickName = authStore.userInfo.nickName || authStore.userInfo.userName;
  profileModel.userGender = authStore.userInfo.userGender || '3';
  profileModel.userEmail = authStore.userInfo.userEmail;
  profileModel.userPhone = authStore.userInfo.userPhone;
}

function normalizeNullable(value: string | null) {
  if (typeof value !== 'string') return value;
  const trimmed = value.trim();
  return trimmed || null;
}

async function handleProfileSubmit() {
  await validateProfile();
  if (profileSubmitting.value) return;

  profileSubmitting.value = true;
  try {
    const { data, error } = await fetchUpdateProfile({
      nickName: normalizeNullable(profileModel.nickName),
      userGender: profileModel.userGender,
      userEmail: normalizeNullable(profileModel.userEmail),
      userPhone: normalizeNullable(profileModel.userPhone)
    });

    if (error) return;

    Object.assign(authStore.userInfo, data);
    syncProfileModel();
    await restoreProfileValidation();
    window.$message?.success($t('common.updateSuccess'));
  } finally {
    profileSubmitting.value = false;
  }
}

async function handlePasswordSubmit() {
  await validatePassword();
  if (passwordSubmitting.value) return;

  passwordSubmitting.value = true;
  try {
    const { error } = await fetchUpdatePassword({
      oldPassword: passwordModel.oldPassword,
      newPassword: passwordModel.newPassword
    });
    if (error) return;

    window.$message?.success($t('page.userCenter.password.success'));
    passwordModel.oldPassword = '';
    passwordModel.newPassword = '';
    passwordModel.confirmPassword = '';
    await restorePasswordValidation();
    await authStore.resetStore();
  } finally {
    passwordSubmitting.value = false;
  }
}

syncProfileModel();
</script>

<template>
  <NSpace vertical :size="16">
    <NCard :title="$t('page.userCenter.profile.title')" :bordered="false" size="small" class="card-wrapper">
      <NSpace vertical :size="16">
        <NDescriptions label-placement="left" :column="2" bordered>
          <NDescriptionsItem :label="$t('page.userCenter.profile.userName')">
            {{ authStore.userInfo.userName }}
          </NDescriptionsItem>
          <NDescriptionsItem :label="$t('page.userCenter.profile.roles')" :span="1">
            <NSpace>
              <NTag v-for="role in authStore.userInfo.roles" :key="role" type="info">
                {{ role }}
              </NTag>
            </NSpace>
          </NDescriptionsItem>
        </NDescriptions>

        <NAlert v-if="authStore.impersonating" type="warning" :title="$t('page.userCenter.profile.impersonating')" />

        <NForm
          ref="profileFormRef"
          :model="profileModel"
          :rules="profileRules"
          label-placement="left"
          label-width="120px"
          require-mark-placement="right-hanging"
          class="max-w-560px"
        >
          <NFormItem :label="$t('page.userCenter.profile.nickName')" path="nickName">
            <NInput v-model:value="profileModel.nickName" :placeholder="$t('page.manage.user.form.nickName')" />
          </NFormItem>
          <NFormItem :label="$t('page.manage.user.userGender')" path="userGender">
            <NRadioGroup v-model:value="profileModel.userGender">
              <NRadio
                v-for="item in translateOptions(userGenderOptions)"
                :key="item.value"
                :value="item.value"
                :label="item.label"
              />
            </NRadioGroup>
          </NFormItem>
          <NFormItem :label="$t('page.manage.user.userEmail')" path="userEmail">
            <NInput v-model:value="profileModel.userEmail" :placeholder="$t('page.manage.user.form.userEmail')" />
          </NFormItem>
          <NFormItem :label="$t('page.manage.user.userPhone')" path="userPhone">
            <NInput v-model:value="profileModel.userPhone" :placeholder="$t('page.manage.user.form.userPhone')" />
          </NFormItem>
          <NFormItem :show-label="false">
            <NButton type="primary" :loading="profileSubmitting" @click="handleProfileSubmit">
              {{ $t('common.update') }}
            </NButton>
          </NFormItem>
        </NForm>
      </NSpace>
    </NCard>

    <NCard :title="$t('page.userCenter.password.title')" :bordered="false" size="small" class="card-wrapper">
      <NForm
        ref="passwordFormRef"
        :model="passwordModel"
        :rules="passwordRules"
        label-placement="left"
        label-width="120px"
        require-mark-placement="right-hanging"
        class="max-w-560px"
      >
        <NFormItem :label="$t('page.userCenter.password.oldPassword')" path="oldPassword">
          <NInput
            v-model:value="passwordModel.oldPassword"
            type="password"
            show-password-on="click"
            :placeholder="$t('page.userCenter.password.oldPasswordPlaceholder')"
          />
        </NFormItem>
        <NFormItem :label="$t('page.userCenter.password.newPassword')" path="newPassword">
          <NInput
            v-model:value="passwordModel.newPassword"
            type="password"
            show-password-on="click"
            :placeholder="$t('page.userCenter.password.newPasswordPlaceholder')"
          />
        </NFormItem>
        <NFormItem :label="$t('page.userCenter.password.confirmPassword')" path="confirmPassword">
          <NInput
            v-model:value="passwordModel.confirmPassword"
            type="password"
            show-password-on="click"
            :placeholder="$t('page.userCenter.password.confirmPasswordPlaceholder')"
          />
        </NFormItem>
        <NFormItem :show-label="false">
          <NButton type="primary" :loading="passwordSubmitting" @click="handlePasswordSubmit">
            {{ $t('page.userCenter.password.submit') }}
          </NButton>
        </NFormItem>
      </NForm>
    </NCard>
  </NSpace>
</template>

<style scoped></style>
