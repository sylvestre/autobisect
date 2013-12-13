// Generate calls to "testing functions" shared between the SpiderMonkey shell and Firefox browser.
// http://mxr.mozilla.org/mozilla-central/source/js/src/builtin/TestingFunctions.cpp

var fuzzTestingFunctions = (function(glob){

  var browser = "window" in glob;

  function tf(funName) {
    if (!browser && (rnd(5) == 0)) {
      // Differential testing hack!
      // Take advantage of the fact that --no-asmjs flips isAsmJSCompilationAvailable().
      // (I couldn't find a better way to communicate from compareJIT to jsfunfuzz:
      // doing --execute='gcslice=function(){}' changes the result of uneval(this)!)
      var cond = (rnd(2) ? "!" : "") + "isAsmJSCompilationAvailable()";
      return "(" + cond + " ? " + funName + " : (function(){}))";
    }
    return browser ? "fuzzPriv." + funName : funName;
  }

  function numberOfAllocs() { return Math.floor(Math.exp(rnd(rnd(6000)) / 1000)); }

  function global(d, b) { return browser ? Things.instance("Window") : makeExpr(d - 1, b); }
  function object(d, b) { return browser ? Things.any() : makeExpr(d - 1, b); }

  function enableGCZeal()
  {
    var level = rnd(14);
    if (browser && level == 9) level = 0; // bug 815241
    var period = numberOfAllocs();
    return tf("gczeal") + "(" + level + ", " + period + ")";
  }

  var testingFunctions = Random.weighted([
    // Force garbage collection (global or specific compartment)
    { w: 10, v: function(d, b) { return "(void " + tf("gc") + "()" + ")"; } },
    { w: 10, v: function(d, b) { return "(void " + tf("gc") + "('compartment')" + ")"; } },
    { w: 5,  v: function(d, b) { return "(void " + tf("gc") + "(" + global(d, b) + ")" + ")"; } },

    // Run a minor garbage collection on the nursery.
    // (void is for bug 940253)
    { w: 20, v: function(d, b) { return "(void " + tf("minorgc") + "(false)" + ")"; } },
    { w: 20, v: function(d, b) { return "(void " + tf("minorgc") + "(true)" + ")"; } },

    // Invoke an incremental garbage collection slice.
    { w: 20, v: function(d, b) { return tf("gcslice") + "(" + Math.floor(Math.pow(2, Random.float() * 32)) + ")"; } },

    // Schedule the given objects to be marked in the next GC slice.
    { w: 10, v: function(d, b) { return tf("selectforgc") + "(" + object(d, b) + ")"; } },

    // Add a compartment to the next garbage collection.
    { w: 10, v: function(d, b) { return tf("schedulegc") + "(" + global(d, b) + ")"; } },

    // Schedule a GC for after N allocations.
    { w: 10, v: function(d, b) { return tf("schedulegc") + "(" + numberOfAllocs() + ")"; } },

    // Make garbage collection extremely frequent (SLOW)
    { w: 1,  v: function(d, b) { return (!browser || rnd(100) == 0) ? (enableGCZeal()) : "0"; } },

    // Verify write barriers. These functions are effective in pairs.
    // The first call sets up the start barrier, the second call sets up the end barrier.
    // Nothing happens when there is only one call.
    { w: 10, v: function(d, b) { return tf("verifyprebarriers") + "()"; } },
    { w: 10, v: function(d, b) { return tf("verifypostbarriers") + "()"; } },

    // Trace the heap using non-GC tracing code
    { w: 1,  v: function(d, b) { return "(void " + tf("countHeap") + "()" + ")"; } },

    // Toggle various validations.
    { w: 5,  v: function(d, b) { return tf("validategc") + "(false)"; } },
    { w: 1,  v: function(d, b) { return tf("validategc") + "(true)"; } },
    { w: 5,  v: function(d, b) { return tf("fullcompartmentchecks") + "(false)"; } },
    { w: 1,  v: function(d, b) { return tf("fullcompartmentchecks") + "(true)"; } },
    { w: 5,  v: function(d, b) { return tf("setIonCheckGraphCoherency") + "(false)"; } },
    { w: 1,  v: function(d, b) { return tf("setIonCheckGraphCoherency") + "(true)"; } },
    { w: 1,  v: function(d, b) { return tf("enableOsiPointRegisterChecks") + "()"; } },

    // Run-time equivalents to --baseline-eager or --baseline-uses-before-compile, --no-baseline, etc
    // (void is for bug 944153)
    { w: 1,  v: function(d, b) { return "(void " + tf("setJitCompilerOption") + "('baseline.usecount.trigger', " + rnd(20) + ")" + ")"; } },
    { w: 1,  v: function(d, b) { return "(void " + tf("setJitCompilerOption") + "('ion.usecount.trigger', " + rnd(40) + ")" + ")"; } },
    //{ w: 1,  v: function(d, b) { return "(void " + tf("setJitCompilerOption") + "('ion.enable', " + rnd(2) + ")" + ")"; } }, // see bug 949807
    //{ w: 1,  v: function(d, b) { return tf("setJitCompilerOption") + "('baseline.enable', " + rnd(2) + ")"; } }, // bug 932284

    // I'm not sure what this does in the shell.
    { w: 5,  v: function(d, b) { return tf("deterministicgc") + "(false)"; } },
    { w: 1,  v: function(d, b) { return tf("deterministicgc") + "(true)"; } },

    // Causes JIT code to always be preserved by GCs afterwards (see https://bugzilla.mozilla.org/show_bug.cgi?id=750834)
    { w: 5,  v: function(d, b) { return tf("gcPreserveCode") + "()"; } },
  ]);

  return { testingFunctions: testingFunctions, enableGCZeal: enableGCZeal }

})(this);
