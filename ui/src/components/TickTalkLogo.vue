<template>
  <div class="ticktalk-logo" aria-label="TickTalk">
    <span class="logo-bubbles" aria-hidden="true">
      <span class="logo-bubble logo-bubble--main">
        <span class="logo-dots"><i /><i /><i /></span>
      </span>
      <span class="logo-bubble logo-bubble--back" />
    </span>
    <span class="logo-wordmark">TickTalk</span>
  </div>
</template>

<style scoped>
.ticktalk-logo {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  justify-content: center;
}
.logo-bubbles {
  position: relative;
  width: 2.5rem;
  height: 2.1rem;
}
.logo-bubble {
  position: absolute;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
.logo-bubble--back {
  left: 0;
  bottom: 0;
  width: 1.35rem;
  height: 1.2rem;
  border-radius: 0.5rem 0.5rem 0.5rem 0.12rem;
  background-color: #2ec4b6; /* Teal back bubble */
}
.logo-bubble--main {
  right: 0;
  top: 0;
  width: 1.68rem;
  height: 1.45rem;
  border-radius: 0.55rem 0.55rem 0.55rem 0.12rem;
  background-color: #ff5252; /* Coral front bubble */
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-dots {
  display: flex;
  gap: 0.15rem;
}
.logo-dots i {
  display: block;
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 50%;
  background-color: #ffffff;
  font-style: normal;
}
.logo-wordmark {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #1e293b;
}
</style>
