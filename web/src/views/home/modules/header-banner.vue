<script setup lang="ts">
import { useAuthStore } from '@/store/modules/auth';
import { $t } from '@/locales';

defineOptions({
  name: 'HeaderBanner'
});

const authStore = useAuthStore();
</script>

<template>
  <NCard :bordered="false" class="card-wrapper">
    <div class="flex-y-center">
      <div class="size-72px shrink-0 overflow-hidden rd-1/2">
        <img src="@/assets/imgs/soybean.jpg" class="size-full" />
      </div>
      <div class="pl-12px">
        <h3 class="text-18px font-semibold">
          {{ $t('page.home.greeting', { userName: authStore.userInfo.userName }) }}
        </h3>
        <p class="text-#999 leading-30px">{{ $t('page.home.weatherDesc') }}</p>
      </div>
    </div>
  </NCard>
</template>

<style scoped></style>
