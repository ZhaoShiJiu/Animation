/**
 * static/postprocess.js —— 客户端动画 HTML 后处理增强
 *
 * 在生成的 HTML 被放入 iframe 之前进行增强：
 *   1. 注入 CSS 设计系统变量（如果缺失）
 *   2. 添加字体抗锯齿
 *   3. 注入背景噪点纹理 SVG
 *   4. 确保 GSAP timeline 注册
 *   5. 修复常见样式问题
 *
 * 用法：
 *   const enhancedHTML = ZSJPostProcess.enhance(rawHTML);
 */

(function (global) {
  'use strict';

  var CSS_VARIABLE_SYSTEM = [
    ':root {',
    '  --color-danger:    #DC2626;',
    '  --color-mystery:   #7C3AED;',
    '  --color-reveal:    #2563EB;',
    '  --color-insight:   #059669;',
    '  --color-memory:    #D97706;',
    '  --color-bg:        #FAFBFC;',
    '  --color-surface:   #FFFFFF;',
    '  --color-text:      #0F172A;',
    '  --color-text-dim:  #64748B;',
    '  --color-border:    #E2E8F0;',
    '  --font-display: "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif;',
    '  --font-body:    "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif;',
    '  --fs-hero:      clamp(3.5rem, 8vw, 7rem);',
    '  --fs-headline:  clamp(2rem, 5vw, 4rem);',
    '  --fs-body:      1.25rem;',
    '  --fs-subtitle:  1.05rem;',
    '  --fs-small:     0.85rem;',
    '  --space-xs:  8px;',
    '  --space-sm:  16px;',
    '  --space-md:  24px;',
    '  --space-lg:  40px;',
    '  --space-xl:  64px;',
    '  --ease-smooth:     cubic-bezier(0.22, 0.61, 0.36, 1);',
    '  --ease-out-back:   cubic-bezier(0.34, 1.56, 0.64, 1);',
    '  --ease-spring:     cubic-bezier(0.175, 0.885, 0.32, 1.275);',
    '  --ease-slow:       cubic-bezier(0.25, 0.1, 0.25, 1);',
    '}'
  ].join('\n');

  var FONT_SMOOTHING = [
    'body {',
    '  -webkit-font-smoothing: antialiased;',
    '  -moz-osx-font-smoothing: grayscale;',
    '  text-rendering: optimizeLegibility;',
    '}'
  ].join('\n');

  var NOISE_TEXTURE_SVG = [
    '<svg aria-hidden="true" class="zsj-noise-texture" style="position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.035;">',
    '  <filter id="zsj-noise-filter">',
    '    <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="4" stitchTiles="stitch"/>',
    '    <feColorMatrix type="saturate" values="0"/>',
    '  </filter>',
    '  <rect width="100%" height="100%" filter="url(#zsj-noise-filter)"/>',
    '</svg>'
  ].join('\n');

  var GSAP_TIMELINE_PATCH = [
    '<script>',
    '(function(){',
    '  if(typeof gsap!=="undefined"&&!window.__timelines){',
    '    var _r=[];',
    '    var _o=gsap.timeline;',
    '    gsap.timeline=function(){var t=_o.apply(gsap,arguments);_r.push(t);return t;};',
    '    Object.defineProperty(window,"__timelines",{get:function(){return _r;},set:function(v){if(Array.isArray(v))_r=v;}});',
    '  }',
    '})();',
    '<\/script>'
  ].join('\n');

  function hasCSSVariables(html) {
    return /--color-\w+\s*:/.test(html);
  }

  function hasFontSmoothing(html) {
    return /-webkit-font-smoothing|font-smooth/.test(html);
  }

  function hasNoiseTexture(html) {
    return /feTurbulence|noise-texture|zsj-noise/.test(html);
  }

  function hasGSAP(html) {
    return /gsap.*\.js|greensock/i.test(html);
  }

  function hasTimelines(html) {
    return /window\.__timelines/.test(html);
  }

  function stripMarkdownFences(html) {
    html = html.trim();
    html = html.replace(/^```(?:html|HTML)?\s*\n?/, '');
    html = html.replace(/\n?```\s*$/, '');
    return html.trim();
  }

  function injectIntoStyle(html, css) {
    var styleMatch = /<style[^>]*>/i.exec(html);
    if (styleMatch) {
      var pos = styleMatch.index + styleMatch[0].length;
      return html.slice(0, pos) + '\n' + css + '\n' + html.slice(pos);
    }
    // No <style> tag, inject before </head>
    if (/<\/head>/i.test(html)) {
      return html.replace(/<\/head>/i, '<style>\n' + css + '\n</style>\n</head>');
    }
    return html;
  }

  function injectBeforeBodyClose(html, content) {
    if (/<\/body>/i.test(html)) {
      return html.replace(/<\/body>/i, content + '\n</body>');
    }
    if (/<\/html>/i.test(html)) {
      return html.replace(/<\/html>/i, content + '\n</html>');
    }
    return html + '\n' + content;
  }

  function injectAfterBody(html, content) {
    var match = /<body[^>]*>/i.exec(html);
    if (match) {
      var pos = match.index + match[0].length;
      return html.slice(0, pos) + '\n' + content + '\n' + html.slice(pos);
    }
    return html;
  }

  function ensureBodyOverflowHidden(html) {
    var match = /<body([^>]*)>/i.exec(html);
    if (match && !/overflow/i.test(match[1])) {
      var newBody = '<body' + match[1] + ' style="overflow:hidden">';
      return html.slice(0, match.index) + newBody + html.slice(match.index + match[0].length);
    }
    return html;
  }

  /**
   * 验证 JSON segment 数据块是否可解析，输出警告日志。
   * @param {string} html
   * @returns {number} 无效 segment 数量
   */
  function validateSegments(html) {
    var pattern = /<script\s+type=["']application\/json["']\s+id=["']seg-data-(\d+)["']\s*>([\s\S]*?)<\/script>/gi;
    var badCount = 0;
    var match;
    while ((match = pattern.exec(html)) !== null) {
      var segId = match[1];
      var content = match[2].trim();
      if (!content) {
        console.warn('[ZSJ PostProcess] JSON segment ' + segId + ' is empty');
        badCount++;
        continue;
      }
      try {
        JSON.parse(content);
      } catch (e) {
        console.warn('[ZSJ PostProcess] JSON segment ' + segId + ' parse failed:', e.message);
        console.warn('[ZSJ PostProcess] Raw (first 150 chars):', content.substring(0, 150));
        badCount++;
      }
    }
    if (badCount > 0) {
      console.warn('[ZSJ PostProcess] ' + badCount + ' JSON segment(s) have issues — animation may be incomplete');
    }
    return badCount;
  }

  /**
   * 对动画 HTML 进行全面的客户端增强。
   * @param {string} html - 原始 HTML
   * @param {{injectCSS?: boolean, injectNoise?: boolean, injectGSAPPatch?: boolean, fixOverflow?: boolean}} options
   * @returns {string} 增强后的 HTML
   */
  function enhance(html, options) {
    options = options || {};
    var injectCSS = options.injectCSS !== false;
    var injectNoise = options.injectNoise !== false;
    var injectGSAPPatch = options.injectGSAPPatch !== false;
    var fixOverflow = options.fixOverflow !== false;

    if (!html || typeof html !== 'string') return html;

    html = stripMarkdownFences(html);

    var patches = [];

    // 1. 注入 CSS 变量系统
    if (injectCSS && !hasCSSVariables(html)) {
      html = injectIntoStyle(html, CSS_VARIABLE_SYSTEM);
      patches.push('css-vars');
    }

    // 2. 注入字体抗锯齿
    if (injectCSS && !hasFontSmoothing(html)) {
      html = injectIntoStyle(html, FONT_SMOOTHING);
      patches.push('font-smoothing');
    }

    // 3. 注入背景噪点纹理
    if (injectNoise && !hasNoiseTexture(html)) {
      html = injectAfterBody(html, NOISE_TEXTURE_SVG);
      patches.push('noise-texture');
    }

    // 4. 注入 GSAP timeline 注册补丁
    if (injectGSAPPatch && hasGSAP(html) && !hasTimelines(html)) {
      html = injectBeforeBodyClose(html, GSAP_TIMELINE_PATCH);
      patches.push('gsap-timeline-patch');
    }

    // 5. 修复 body overflow
    if (fixOverflow) {
      var before = html;
      html = ensureBodyOverflowHidden(html);
      if (html !== before) patches.push('overflow-fix');
    }

    // 6. 验证 JSON segment 数据块
    var badSegments = validateSegments(html);
    if (badSegments > 0) {
      patches.push(badSegments + ' bad JSON segments');
    }

    // 7. 自动补全缺失的闭合标签（LLM 截断防护）
    var closeResult = ensureClosingTags(html);
    html = closeResult.html;
    if (closeResult.closed.length > 0) {
      patches.push('auto-closed: ' + closeResult.closed.join(', '));
    }

    if (patches.length > 0) {
      console.log('[ZSJ PostProcess] Applied patches:', patches.join(', '));
    }

    return html;
  }

  /**
   * 自动补全缺失的 </script> </body> </html> 闭合标签。
   */
  function ensureClosingTags(html) {
    var closed = [];

    if (!/<\/script>/i.test(html)) {
      var lastScript = Math.max(html.lastIndexOf('<script>'), html.lastIndexOf('<script '));
      if (lastScript !== -1) {
        html = html.replace(/\s*$/, '') + '\n})();\n</script>';
        closed.push('</script>+IIFE');
      }
    }

    if (!/<\/body>/i.test(html)) {
      html = html.replace(/\s*$/, '') + '\n</body>';
      closed.push('</body>');
    }

    if (!/<\/html>/i.test(html)) {
      html = html.replace(/\s*$/, '') + '\n</html>';
      closed.push('</html>');
    }

    return { html: html, closed: closed };
  }

  // Expose
  global.ZSJPostProcess = {
    enhance: enhance,
    validateSegments: validateSegments,
    ensureClosingTags: ensureClosingTags,
    hasCSSVariables: hasCSSVariables,
    hasGSAP: hasGSAP,
    hasTimelines: hasTimelines,
    hasNoiseTexture: hasNoiseTexture
  };

})(typeof window !== 'undefined' ? window : this);
